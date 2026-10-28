from reports.models import Report
from django.forms import ModelForm, RadioSelect, Textarea, CharField

REASON_HINTS = {
    "Counterfeit": "Barang palsu atau tiruan.",
    "Misleading": "Foto atau deskripsi tidak sesuai.",
    "Offensive": "Konten menyinggung.",
    "Prohibited Item": "Barang yang dilarang.",
    "Other": "Alasan lain.",
}

class ReportModerationForm(ModelForm):
    moderator_note = CharField(
        label="Catatan Moderator",
        widget=Textarea(attrs={
                            "placeholder": "Tuliskan alasan keputusan untuk tim..",
                            "rows": 4,
                        }),
        required=True
    )
    class Meta:
        model = Report
        fields = [
            'status',
        ]
        labels = {
            'status': 'status laporan',
        }
        widgets = {
            'status': RadioSelect(
                attrs={
                    "required" : True,
                    "class": "status-select",
                }
            ),
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
        
    @property
    def reason_options(self):
        # (nilai, keterangan, apakah terpilih) untuk daftar radio di template.
        selected = self["reason"].value()
        return [
            (value, REASON_HINTS.get(value, ""), value == selected)
            for value, _label in self.fields["reason"].choices
            if value != ""
        ]
    
    