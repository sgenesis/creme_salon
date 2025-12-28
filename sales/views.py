from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Sale, SaleItem
from .serializers import SaleSerializer
from reportlab.pdfgen import canvas
from django.http import FileResponse, HttpResponse
from django.db.models import Count
from datetime import date, timedelta
from rest_framework.permissions import IsAuthenticated
import openpyxl
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required



@method_decorator(ensure_csrf_cookie, name='dispatch')
class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all().order_by('-date')
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)

# 📌 Historial por cliente
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sales_by_client(request, client_id):
    sales = Sale.objects.filter(client_id=client_id)
    return Response(SaleSerializer(sales, many=True).data)

# 📌 Reporte global por fechas
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sales_report(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    qs = Sale.objects.all()
    if start and end:
        qs = qs.filter(date__range=[start, end])
    total = qs.aggregate(total=Sum('total'))['total'] or 0
    return Response({
        "total_sales": total,
        "count": qs.count(),
        "sales": SaleSerializer(qs, many=True).data
    })

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sale_ticket(request, sale_id):
    sale = Sale.objects.get(id=sale_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{sale_id}.pdf"'

    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "TICKET DE COMPRA")

    p.setFont("Helvetica", 12)
    p.drawString(40, 760, f"Cliente: {sale.client.username}")
    p.drawString(40, 740, f"Fecha: {sale.date.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(40, 720, f"Método de pago: {sale.payment_method}")
    p.drawString(40, 700, f"Total: ${sale.total}")

    y = 660
    for item in sale.items.all():
        p.drawString(60, y, f"- {item.product.name if item.product else 'Servicio'}  ${item.subtotal}")
        y -= 20

    p.showPage()
    p.save()
    return response

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def sales_history(request):
    start = request.GET.get("start")
    end = request.GET.get("end")

    sales = Sale.objects.all().order_by("-date")

    if start and end:
        sales = sales.filter(date__date__range=[start, end])

    return Response(SaleSerializer(sales, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_dashboard(request):
    from datetime import date

    qs = Sale.objects.all()
    today = date.today()
    month_start = today.replace(day=1)

    total_sales = qs.aggregate(total=Sum('total'))['total'] or 0
    count_sales = qs.count()
    today_sales = qs.filter(date__date=today).aggregate(t=Sum('total'))['t'] or 0
    month_sales = qs.filter(date__date__gte=month_start).aggregate(t=Sum('total'))['t'] or 0

    by_payment = qs.values('payment_method').annotate(
        total=Sum('total'), count=Count('id')
    )

    by_day = qs.extra({"day": "date(date)"}).values("day").annotate(
        total=Sum("total"), count=Count("id")
    ).order_by("day")[:15]

    top = SaleItem.objects.values('product__name').annotate(
        total=Sum('subtotal'), count=Count('id')
    ).order_by('-total')[:5]

    return Response({
        "summary": {
            "total_sales": float(total_sales),
            "count_sales": count_sales
        },
        "today_sales": float(today_sales),
        "month_sales": float(month_sales),
        "by_payment": list(by_payment),
        "by_day": list(by_day),
        "top_items": list(top)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sales_export_excel(request):
    # Filtros opcionales de fecha
    start = request.GET.get("start")
    end = request.GET.get("end")

    sales = Sale.objects.all().order_by("-date")

    if start and end:
        sales = sales.filter(date__date__range=[start, end])

    wb = openpyxl.Workbook()

    # 🧠 HOJA 1 — DASHBOARD RESUMEN
    ws1 = wb.active
    ws1.title = "Resumen"

    total_ventas = sales.aggregate(t=Sum("total"))["t"] or 0
    count_ventas = sales.count()

    # Métodos de pago
    by_payment = sales.values("payment_method").annotate(
        total=Sum("total"), count=Count("id")
    )

    # Top 5 items vendidos
    top_items = SaleItem.objects.filter(sale__in=sales).values(
        "product__name"
    ).annotate(total=Sum("subtotal"), count=Count("id")).order_by("-total")[:5]

    ws1.append(["📊 REPORTE DE VENTAS"])
    ws1.append([
        f"Rango de fechas: {start if start else 'Inicio'} a {end if end else 'Hoy'}"
    ])
    ws1.append([])

    ws1.append(["Total vendido", float(total_ventas)])
    ws1.append(["Cantidad de ventas", count_ventas])
    ws1.append([])

    # Métodos de pago
    ws1.append(["Métodos de pago"])
    ws1.append(["Método", "Cantidad", "Total"])
    for m in by_payment:
        ws1.append([m["payment_method"], m["count"], float(m["total"])])
    ws1.append([])

    # Top items
    ws1.append(["Top servicios/productos"])
    ws1.append(["Producto/Servicio", "Veces vendido", "Total vendido"])
    for t in top_items:
        ws1.append([t["product__name"] or "Servicio", t["count"], float(t["total"])])

    # 🧾 HOJA 2 — DETALLE
    ws2 = wb.create_sheet("Detalle de ventas")

    headers = [
        "Fecha Venta", "Cliente", "Cita Fecha/Hora", "Método pago",
        "Producto/Servicio", "Cantidad", "Subtotal Item", "Total Venta"
    ]
    ws2.append(headers)

    total_items = 0

    for sale in sales:
        items = sale.items.all()
        appt = getattr(sale, "appointment", None)
        cita = appt.date.strftime("%Y-%m-%d %H:%M") if appt and hasattr(appt, "date") else "-"

        if not items:
            ws2.append([
                sale.date.strftime("%Y-%m-%d %H:%M"),
                sale.client.username if sale.client else "N/A",
                cita,
                sale.payment_method,
                "-", "-", "-",
                float(sale.total)
            ])
        else:
            for item in items:
                total_items += 1
                ws2.append([
                    sale.date.strftime("%Y-%m-%d %H:%M"),
                    sale.client.username if sale.client else "N/A",
                    cita,
                    sale.payment_method,
                    item.product.name if item.product else "Servicio",
                    item.quantity if hasattr(item, "quantity") else 1,
                    float(item.subtotal),
                    float(sale.total)
                ])

    ws2.append([])
    ws2.append(["Resumen"])
    ws2.append(["Total ventas:", count_ventas])
    ws2.append(["Total items vendidos:", total_items])
    ws2.append(["Ingreso total:", float(total_ventas)])

    # Descargar
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_ventas.xlsx"'
    wb.save(response)
    return response

@login_required
def quick_sale_view(request):
    # solo admin o staff? lo dejamos accesible a quienes usen la interfaz: staff/admin
    if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        return redirect('/api/appointments/available-view/')
    return render(request, 'sales/ventas_rapidas.html')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_cut(request):
    from django.utils import timezone

    today = timezone.localdate()
    sales = Sale.objects.filter(date__date=today)

    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    count_sales = sales.count()

    # Desglose por método de pago
    payments = sales.values('payment_method').annotate(
        total=Sum('total'), count=Count('id')
    )

    # Items vendidos
    items = SaleItem.objects.filter(sale__in=sales).values(
        'product__name'
    ).annotate(
        total=Sum('subtotal'),
        count=Count('id')
    ).order_by('-total')

    return Response({
        "date": today,
        "total_sales": float(total_sales),
        "count_sales": count_sales,
        "by_payment": list(payments),
        "items": list(items),
        "sales": SaleSerializer(sales, many=True).data
    })


@login_required
def daily_cut_view(request):
    return render(request, "sales/corte_diario.html")
