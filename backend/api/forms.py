from django import forms
from .models import Cargo

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = [
            'loading_city_primary',
            'unloading_city_primary',
            'date_from',
            'cargo_type',
            'weight',
        ]