from django import forms


class CSVUploadForm(forms.Form):

    file = forms.FileField(
        label="CSVファイル",
        help_text="UTF-8形式のCSVファイルを選択してください。"
    )

    def clean_file(self):

        file = self.cleaned_data["file"]

        if not file.name.lower().endswith(".csv"):
            raise forms.ValidationError(
                "CSVファイルを選択してください。"
            )

        return file