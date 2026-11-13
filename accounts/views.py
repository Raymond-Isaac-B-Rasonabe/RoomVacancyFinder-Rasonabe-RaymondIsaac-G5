from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from .decorators import role_required
from .forms import SignUpForm, ProfileForm
from .models import User

def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. You can log in now.")
            return redirect("login")
        messages.error(request, "Please fix the errors below.")
    return render(request, "form.html", {"form": form, "title": "Sign up"})

class CustomLoginView(LoginView):
    template_name = "form.html"
    extra_context = {"title": "Log in"}
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)

@login_required
def dashboard_redirect(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("admin_dashboard")
    return redirect("user_dashboard")

@role_required("student", "staff")
def user_dashboard(request):
    return render(request, "user_dashboard.html")

@role_required("admin")
def admin_dashboard(request):
    return render(request, "admin_dashboard.html", {"user_count": User.objects.count()})

@login_required
def profile(request):
    return render(request, "profile.html")

@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
        messages.error(request, "Please fix the errors below.")
    return render(request, "form.html", {"form": form, "title": "Edit profile"})