from reports.models import Report
from django.forms import ModelForm, RadioSelect, Textarea

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
            "category" : RadioSelect(
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
    
    