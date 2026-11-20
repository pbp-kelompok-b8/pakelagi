from django.core.validators import MaxLengthValidator
from django.db import IntegrityError, transaction
from django.forms import ModelForm, RadioSelect, Textarea

from reports.models import DUPLICATE_REPORT_CONSTRAINT, DUPLICATE_REPORT_MESSAGE, Report

REASON_HINTS = {
    "Counterfeit": "Barang palsu atau tiruan.",
    "Misleading": "Foto atau deskripsi tidak sesuai.",
    "Offensive": "Konten menyinggung.",
    "Prohibited Item": "Barang yang dilarang.",
    "Other": "Alasan lain.",
}
        
class ReportForm(ModelForm):
    class Meta:
        model = Report
        fields = [
            "reason",
            "description",
        ]
        
        labels = {
            "reason":"Alasan Laporan",
            "description":"Deskripsi Laporan",
        }
        
        widgets = {    
            "reason" : RadioSelect(
                attrs={
                    "required" : True,
                    "class": "reason-select",
                }
            ),
            "description" : Textarea(
                attrs={
                    "placeholder": "Jelaskan apa yang tidak sesuai agar moderator punya konteks",
                    "rows": 4,
                }
            ),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Drop the blank "---------" option so only the real reasons are shown
        self.fields["reason"].choices = [c for c in self.fields["reason"].choices if c[0] != ""]

    def clean_description(self):
        description = self.cleaned_data["description"]
        MaxLengthValidator(1000)(description)
        return description

    def save_new(self):
        try:
            with transaction.atomic():
                return self.save()
        except IntegrityError as exc:
            # PostgreSQL reports the constraint name; SQLite does not.
            constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
            duplicate = (constraint == DUPLICATE_REPORT_CONSTRAINT if constraint
                         else self.instance.has_active_duplicate())
            if not duplicate:
                raise
            self.add_error(None, DUPLICATE_REPORT_MESSAGE)
            return None

    @property
    def reason_options(self):
        # (nilai, keterangan, apakah terpilih) untuk daftar radio di template.
        selected = self["reason"].value()
        return [
            (value, REASON_HINTS.get(value, ""), value == selected)
            for value, _label in self.fields["reason"].choices
            if value != ""
        ]
    
    