from .models import Project

def projects_context(request):
    if request.user.is_authenticated:
        owned = Project.objects.filter(owner=request.user)
        member = Project.objects.filter(members=request.user)
        projects = (owned | member).distinct().order_by('name')[:10]
        return {'projects': projects}
    return {}
