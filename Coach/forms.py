from django.forms import ModelForm
from Coach.models import Coach
from django.utils.html import strip_tags

class CoachForm(ModelForm):
    class Meta:
        model = Coach
        fields = ["name", "price", "description", "category", "location",]

        def clean_title(self):
            name = self.cleaned_data["name"]
            return strip_tags(name)

        def clean_content(self):
            description = self.cleaned_data["description"]
            return strip_tags(description)