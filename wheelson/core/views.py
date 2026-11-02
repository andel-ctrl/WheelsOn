"""
WheelsOn Core - Views
"""

from django.shortcuts import render


def dashboard(request):
    """Vista principal del dashboard."""
    context = {
        'app_name': 'WheelsOn',
        'page_title': 'Dashboard',
    }
    return render(request, 'dashboard.html', context)
