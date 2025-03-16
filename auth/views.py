from django.shortcuts import render

# Create your views here.

def api_documentation(request):
    return render(request, "index.html")

