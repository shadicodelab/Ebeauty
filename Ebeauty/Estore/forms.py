from django import forms
from .models import OrderDelivery

class OrderForm(forms.ModelForm):
    class Meta:
        model = OrderDelivery
        fields = ['full_name', 'delivery_location', 'phone_number']