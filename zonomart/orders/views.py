from django.http.response import JsonResponse
from carts.models import CartItem
from django.shortcuts import redirect, render

from store.models import Product
from .forms import OrderForm
from .models import Order, OrderProduct, Payment
import datetime
import json

#email
from django.template.loader import render_to_string
from django.core.mail import EmailMessage




def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(user=request.user, is_ordered=False, order_number=body['orderID'])
    # store details in payment model
    payment = Payment(
        user = request.user,
        payment_id = body['transID'],
        payment_method = body['payment_method'],
        amount_paid = order.order_total,
        status = body['status'],
    )
    payment.save()
    order.payment = payment
    order.is_ordered = True
    order.save()

    #move the cart items to order product table
    cart_items = CartItem.objects.filter(user = request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        order_product.payment = payment
        order_product.user_id = request.user.id
        order_product.product_id = item.product_id
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True
        order_product.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        order_product = OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variation)
        order_product.save()

        #reduce the quantity to sold product
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    #clear the cart
    CartItem.objects.filter(user = request.user).delete()

    #senf the order receive email to customer
    mail_subject = 'ThankYou for your order.'
    message = render_to_string('orders/order_received_email.html',{
        'user' : request.user,
        'order': order,
    })
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()

    #send order number and trans data back to sendData method via json responce
    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }

    return JsonResponse(data)






def place_order(request, total = 0, quantity = 0):
    current_user = request.user

    #if cart count empty
    cart_items = CartItem.objects.filter(user = current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')

    grand_total = 0
    tax = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
    tax = (2*total)/100
    grand_total = total+tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # store the info into the database
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            #generate order number
            yr = int(datetime.date.today().strftime("%Y"))
            dt = int(datetime.date.today().strftime("%d"))
            mt = int(datetime.date.today().strftime("%m"))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            order_number = current_date+str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user, is_ordered = False, order_number=order_number)
            context = {
                'order':order,
                'cart_items':cart_items,
                'total':total,
                'tax':tax,
                'grand_total':grand_total,

            }
            return render(request, 'orders/payments.html', context)
    else:
        return redirect('checkout')





def order_complete(request):
    order_number = request.GET.get('order_number')
    payment_id = request.GET.get('payment_id')

    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)

        subtotal = 0
        for i in ordered_products:
            subtotal += i.product_price * i.quantity

        payment = Payment.objects.get(payment_id=payment_id)

        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'payment_id':payment.payment_id,
            'payment':payment,
            'subtotal':subtotal,
        }

        return render(request, 'orders/order_complete.html', context)

    except(Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')