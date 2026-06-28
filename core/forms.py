import hashlib
from django import forms
from .models import Document


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej: Contrato de arrendamiento'}),
            'file': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': '.pdf,.doc,.docx,.png,.jpg,.jpeg'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('El archivo no puede superar los 50MB.')
            file.seek(0)
            sha = hashlib.sha256()
            for chunk in file.chunks():
                sha.update(chunk)
            file.seek(0)
            self._hash = sha.hexdigest()
        return file

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.hash_sha256 = getattr(self, '_hash', '')
        if commit:
            instance.save()
        return instance
