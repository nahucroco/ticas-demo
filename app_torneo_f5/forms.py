from django import forms
from .models import PartidoAmistoso
import json
import os
from django.forms import DateInput
from django.contrib.auth import get_user_model
from datetime import datetime, time
from django.conf import settings
from django.core.exceptions import ValidationError
from app_torneo_f5.models import Jugador, Equipo, PartidoAmistoso, Partido, EstadisticaAmistosa, EstadisticaJugador, EstadisticasJugadorPartido
from django.utils import timezone
User = get_user_model()
from django.contrib.contenttypes.models import ContentType
from datetime import date
from django.forms import Select


class PartidoAmistosoForm(forms.ModelForm):
    cancha = forms.ChoiceField(choices=[])

    class Meta:
        model = PartidoAmistoso
        fields = ['jugadores', 'dia', 'hora_inicio', 'duracion', 'tipo_cancha', 'precio_total', 'max_jugadores']
        widgets = {
            'jugadores': forms.SelectMultiple(attrs={'id': 'id_jugadores'}),
            'dia': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'duracion': forms.NumberInput(attrs={'min': 60, 'step': 15, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Cargar canchas desde JSON
        try:
            json_path = os.path.join(settings.BASE_DIR, 'app_torneo_f5', 'static', 'canchas.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                canchas = json.load(f)
            self.fields['cancha'].choices = [(c['nombre'], c['nombre']) for c in canchas]
            self.canchas_data = {c['nombre']: c['direccion'] for c in canchas}
        except Exception as e:
            print(f"Error cargando canchas.json: {e}")
            self.fields['cancha'].choices = []
            self.canchas_data = {}

        self.fields['jugadores'].queryset = Jugador.objects.all()

        if self.instance and hasattr(self.instance, 'nombre_cancha') and 'cancha' in self.fields:
            self.initial['cancha'] = self.instance.nombre_cancha

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.dia = self.cleaned_data['dia']
        instance.hora_inicio = self.cleaned_data['hora_inicio']

        cancha_nombre = self.cleaned_data.get('cancha')
        instance.nombre_cancha = cancha_nombre
        instance.ubicacion = self.canchas_data.get(cancha_nombre, 'Sin definir')

        if commit:
            instance.save()
            self.save_m2m()

        return instance

# app_torneo_f5/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

User = get_user_model()

class RegistroManualForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    confirm_password = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')

    class Meta:
        model = User                      # 👈 MUY IMPORTANTE: usa AUTH_USER_MODEL
        fields = ['username', 'email', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe un usuario con ese email.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Las contraseñas no coinciden.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.full_name = f"{user.first_name} {user.last_name}".strip() or None
        if commit:
            user.save()
        return user
    
class EstadisticasJugadorPartidoForm(forms.ModelForm):
    class Meta:
        model = EstadisticasJugadorPartido
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class EstadisticaAmistosaForm(forms.ModelForm):
    class Meta:
        model = EstadisticaAmistosa
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
class CrearPerfil1Form(forms.ModelForm):
    fecha_nacimiento = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Jugador
        fields = ['nombre', 'foto', 'fecha_nacimiento', 'altura']

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha:
            hoy = date.today()
            edad = hoy.year - fecha.year - ((hoy.month, hoy.day) < (fecha.month, fecha.day))
            self.cleaned_data['edad'] = edad
        return fecha

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.edad = self.cleaned_data.get('edad')
        instance.fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')
        if commit:
            instance.save()
        return instance

class CrearPerfil2Form(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['posicion_preferida']

class CrearPerfil3Form(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['pie_preferido']
        
class CrearPerfil4Form(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['ciudad', 'provincia']
        
class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['nombre', 'altura', 'provincia', 'ciudad', 'fecha_nacimiento', 'posicion_preferida', 'pie_preferido', 'fortalezas', 'debilidades', 'foto']
        widgets = {
            'fecha_nacimiento': DateInput(attrs={'type': 'date'}),
            'posicion_preferida': Select(attrs={'class': 'input-custom'}),
            'pie_preferido': Select(attrs={'class': 'input-custom'}),
        }
    def __init__(self, *args, **kwargs):
        super(JugadorForm, self).__init__(*args, **kwargs)

        # Campos obligatorios
        campos_obligatorios = [
            'nombre',
            'altura',
            'ciudad',
            'provincia',
            'fecha_nacimiento',
            'posicion_preferida',
            'pie_preferido',
            'foto',
        ]
        for field in campos_obligatorios:
            self.fields[field].required = True

        # Campos no obligatorios
        self.fields['fortalezas'].required = False
        self.fields['debilidades'].required = False


# app_torneo_f5/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate

class LoginForm(AuthenticationForm):
    def clean(self):
        # Construye cleaned_data con las validaciones de "required" por campo
        forms.Form.clean(self)

        username = self.data.get('username', '').strip()
        password = self.data.get('password', '')

        # Si faltan, dejá que los "required" hagan lo suyo
        if not username or not password:
            return self.cleaned_data

        User = get_user_model()

        # 1) usuario existe?
        try:
            User._default_manager.get_by_natural_key(username)
        except User.DoesNotExist:
            self.add_error('username', 'El usuario no existe.')
            return self.cleaned_data  # inválido por tener errores

        # 2) contraseña correcta?
        user = authenticate(self.request, username=username, password=password)
        if user is None:
            self.add_error('password', 'Contraseña incorrecta.')
            return self.cleaned_data  # inválido

        # 3) ok -> permitir login
        self.confirm_login_allowed(user)
        self.user_cache = user
        return self.cleaned_data
