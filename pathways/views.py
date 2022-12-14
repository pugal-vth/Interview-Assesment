from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from . import forms
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
from .models import Application
import locale
import datetime

# Create your views here.
def home(request):
    context = {}
    context['isHomepage'] = True
    return render(request, 'pathways/home.html', context)

def about(request):
    return render(request, 'pathways/about.html', {'title':'About'})

def debugsessionview(request):
    context = {}
    return render(request, 'pathways/debug-session.html', context)

# Considerations between Class-Based Views and Function-Based Views
# https://www.reddit.com/r/django/comments/ad7ulo/when_and_how_to_use_django_formview/edg21b6/

class ApplyView(TemplateView):
    template_name = 'pathways/apply/overview.html'

    def dispatch(self, request, *args, **kwargs):
        for key in list(request.session.keys()):
            del request.session[key]
        return super(ApplyView, self).dispatch(request, *args, **kwargs)

class HouseholdView(FormView):
    template_name = 'pathways/apply/household-size.html'
    form_class = forms.HouseholdForm
    success_url = '/apply/household-benefits/'

    def get_initial(self):
        initial = super(HouseholdView, self).get_initial()
        if 'household' in self.request.session:
            initial['household'] = self.request.session['household']
        return initial

    def form_valid(self, form):
        self.request.session['household'] = form.cleaned_data['household']
        self.request.session['active_app'] = True
        return super().form_valid(form)

# Step 2
class HouseholdBenefitsView(FormView):
    template_name = 'pathways/apply/household-benefits.html'
    form_class = forms.HouseholdBenefitsForm
    success_url = '/apply/income-methods/'

    def form_valid(self, form):
        hasHouseholdBenefits = form.cleaned_data['hasHouseholdBenefits']
        self.request.session['hasHouseholdBenefits'] = form.cleaned_data['hasHouseholdBenefits']
        if hasHouseholdBenefits == 'True':
            self.success_url = '/apply/eligibility/'
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(HouseholdBenefitsView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# TODO: Refactor IncomeViews into single view with conditional for which method was selected, using ContextMixins
# Step 3
class IncomeMethodsView(TemplateView):
    template_name = 'pathways/apply/income-methods.html'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(IncomeMethodsView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Step 4 (exact)
class ExactIncomeView(FormView):
    template_name = 'pathways/apply/exact-income.html'
    form_class = forms.ExactIncomeForm
    success_url = '/apply/review-eligibility/'

    def form_valid(self, form):
        self.request.session = processIncomeHelper(self,form)
        self.request.session['income_method'] = 'exact'
        return super().form_valid(form)
    
    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(ExactIncomeView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Step 4 (hourly)
class HourlyIncomeView(FormView):
    template_name = 'pathways/apply/hourly-income.html'
    form_class = forms.HourlyIncomeForm
    success_url = '/apply/review-eligibility/'

    def form_valid(self, form):
        self.request.session = processIncomeHelper(self,form)
        self.request.session['income_method'] = 'hourly'
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(HourlyIncomeView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Step 4 (estimate)
class EstimateIncomeView(FormView):
    template_name = 'pathways/apply/estimate-income.html'
    form_class = forms.EstimateIncomeForm
    success_url = '/apply/review-eligibility/'

    def form_valid(self, form):
        self.request.session = processIncomeHelper(self,form)
        self.request.session['income_method'] = 'estimate'
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(EstimateIncomeView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Income Helpers
def processIncomeHelper(general_income_view, form):
    """Returns modified session after calculating annual income from form"""
    income = form.cleaned_data['income']
    pay_period = form.cleaned_data['pay_period']
    annual_income = calculateIncomeHelper(income, pay_period)
    general_income_view.request.session['annual_income'] = annual_income
    general_income_view.request.session['income'] = income
    general_income_view.request.session['pay_period'] = pay_period
    return general_income_view.request.session

def calculateIncomeHelper(income, pay_period):
    """Returns annual income based on income each pay_period"""
    if pay_period == 'weekly':
        annual_income = income*50
    elif pay_period == 'biweekly':
        annual_income = income*25
    elif pay_period == 'semimonthly':
        annual_income = income*24
    elif pay_period == 'monthly':
        annual_income = income*12
    else:
        annual_income = income*pay_period*50 #Hourly
    return annual_income
# End Income Helpers

# Step 5
class ReviewEligibilityView(TemplateView):
    template_name = 'pathways/apply/review-eligibility.html'

    # https://stackoverflow.com/questions/5433172/how-to-redirect-on-conditions-with-class-based-views-in-django-1-3/12021673
    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(ReviewEligibilityView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['apply_step'] = 'review-eligibility'
        locale.setlocale( locale.LC_ALL, '' )

        context['annual_income_formatted'] = '${:,.0f}'.format(self.request.session['annual_income'])
        context['income_formatted'] = '${:,.0f}'.format(self.request.session['income'])
        context['pay_period'] = self.request.session['pay_period']
        context['income_method'] = self.request.session['income_method']
        return context

# Step 6
class EligibilityView(TemplateView):
    template_name = 'pathways/apply/eligibility.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hasHouseholdBenefits'] = self.request.session['hasHouseholdBenefits']
        if self.request.session['hasHouseholdBenefits'] == 'True':
            context['isEligible'] = True
        else:
            context['isEligible'] = int(self.request.session['annual_income']) <= incomeLimits[int(self.request.session['household'])]
            locale.setlocale( locale.LC_ALL, '' )
            context['income_formatted'] = locale.currency(
                self.request.session['annual_income'], grouping=True)
            context['income_limit'] = locale.currency(
                incomeLimits[int(self.request.session['household'])], grouping=True)
        return context

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(EligibilityView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

incomeLimits = {
    1: 41850,
    2: 47800,
    3: 53800,
    4: 59750,
    5: 64550,
    6: 69350,
    7: 74100,
    8: 78900,
}

# Step 7
class AdditionalQuestionsView(TemplateView):
    template_name = 'pathways/apply/additional-questions.html'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(AdditionalQuestionsView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Step 8
class ResidentInfoView(FormView):
    template_name = 'pathways/apply/resident-info.html'
    form_class = forms.ResidentInfoForm
    success_url = '/apply/address/'

    def form_valid(self, form):
        self.request.session['first_name'] = form.cleaned_data['first_name']
        self.request.session['last_name'] = form.cleaned_data['last_name']
        self.request.session['middle_initial'] = form.cleaned_data['middle_initial']
        self.request.session['rent_or_own'] = form.cleaned_data['rent_or_own']
        self.request.session['account_holder'] = form.cleaned_data['account_holder']
        #  Redirects to fill in account holder info
        if self.request.session['account_holder'] in ['landlord', 'other']:
            self.success_url = '/apply/account-holder/'
        else:
            self.request.session['account_first'] = form.cleaned_data['first_name']
            self.request.session['account_last'] = form.cleaned_data['last_name']
            self.request.session['account_middle'] = form.cleaned_data['middle_initial']
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(ResidentInfoView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

# Step 9
class AccountHolderView(FormView):
    template_name = 'pathways/apply/info-form.html'
    form_class = forms.AccountHolderForm
    success_url = '/apply/address/'

    def form_valid(self, form):
        self.request.session['account_first'] = form.cleaned_data['account_first']
        self.request.session['account_last'] = form.cleaned_data['account_last']
        self.request.session['account_middle'] = form.cleaned_data['account_middle']
        return super().form_valid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card_title'] = self.form_class.card_title
        return context

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(AccountHolderView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

class AddressView(FormView):
    template_name = 'pathways/apply/info-form.html'
    form_class = forms.AddressForm
    success_url = '/apply/contact-info/'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(AddressView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def form_valid(self, form):
        self.request.session['street_address'] = form.cleaned_data['street_address']
        self.request.session['apartment_unit'] = form.cleaned_data['apartment_unit']
        self.request.session['zip_code'] = form.cleaned_data['zip_code']
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card_title'] = self.form_class.card_title
        return context

class ContactInfoView(FormView):
    template_name = 'pathways/apply/info-form.html'
    form_class = forms.ContactInfoForm
    success_url = '/apply/account-number/'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(ContactInfoView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def form_valid(self, form):
        self.request.session['phone_number'] = form.cleaned_data['phone_number']
        self.request.session['email_address'] = form.cleaned_data['email_address']
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card_title'] = self.form_class.card_title
        return context
        
class AccountNumberView(FormView):
    template_name = 'pathways/apply/info-form.html'
    form_class = forms.AccountNumberForm
    success_url = '/apply/review-application/'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(AccountNumberView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card_title'] = self.form_class.card_title
        context['isAccountNumberView'] = True
        return context

    def form_valid(self, form):
        self.request.session['account_number'] = form.cleaned_data['account_number']
        self.request.session['hasAccountNumber'] = form.cleaned_data['hasAccountNumber']
        return super().form_valid(form)

class ReviewApplicationView(TemplateView):
    template_name = 'pathways/apply/review-application.html'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(ReviewApplicationView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hasHouseholdBenefits'] = self.request.session['hasHouseholdBenefits']
        if self.request.session['hasHouseholdBenefits'] == 'True':
            context['isEligible'] = True
        else:
            locale.setlocale( locale.LC_ALL, '' )
            context['annual_income_formatted'] = '${:,.0f}'.format(self.request.session['annual_income'])
            context['income_formatted'] = '${:,.0f}'.format(self.request.session['income'])
            context['pay_period'] = self.request.session['pay_period']
            context['income_method'] = self.request.session['income_method']
        return context

class LegalView(FormView):
    template_name = 'pathways/apply/legal.html'
    form_class = forms.LegalForm
    success_url = '/apply/signature/'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(LegalView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')
    
    def form_valid(self, form):
        self.request.session['legal_agreement'] = form.cleaned_data['legal_agreement']
        return super().form_valid(form)

class SignatureView(FormView):
    template_name = 'pathways/apply/signature.html'
    form_class = forms.SignatureForm
    success_url = '/apply/documents-overview/'

    def dispatch(self, request, *args, **kwargs):
        if 'active_app' in request.session:
            return super(SignatureView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def form_valid(self, form):
        self.request.session['signature'] = form.cleaned_data['signature']

        app = Application()
        
        # Personal Info
        app.first_name = self.request.session['first_name']
        app.last_name = self.request.session['last_name']
        app.middle_initial = self.request.session['middle_initial']
        app.rent_or_own = self.request.session['rent_or_own']

        app.street_address = self.request.session['street_address']
        app.apartment_unit = self.request.session['apartment_unit']
        app.zip_code = self.request.session['zip_code']

        app.phone_number = self.request.session['phone_number']
        app.email_address = self.request.session['email_address']

        # Billing Info
        app.account_holder = self.request.session['account_holder']
        app.account_first = self.request.session['account_first']
        app.account_last = self.request.session['account_last']
        app.account_middle = self.request.session['account_middle']
        app.account_number = self.request.session['account_number']

        # Eligibility Info
        app.household_size = self.request.session['household']
        app.hasHouseholdBenefits = self.request.session['hasHouseholdBenefits']
        if self.request.session['hasHouseholdBenefits'] == 'False':
            app.annual_income = self.request.session['annual_income']

        # Legal and Signature Info
        app.legal_agreement = self.request.session['legal_agreement']
        app.signature = self.request.session['signature']

        if self.request.session['hasHouseholdBenefits'] == 'False':
            app.annual_income = self.request.session['annual_income']

        app.save()
        self.request.session['app_id'] = app.id

        return super().form_valid(form)

class DocumentOverviewView(TemplateView):
    template_name = 'pathways/docs/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app = Application.objects.filter(id = self.request.session['app_id'])[0]
        context['hasHouseholdBenefits'] = app.hasHouseholdBenefits
        context['rent_or_own'] = app.rent_or_own
        return context

class DocumentIncomeView(FormView):
    template_name = 'pathways/docs/upload-form.html'
    form_class = forms.DocumentIncomeForm
    success_url = '/apply/documents-residence/'

    def dispatch(self, request, *args, **kwargs):
        if self.request.session['hasHouseholdBenefits'] == 'True':
            self.form_class = forms.DocumentBenefitsForm
        else:
            self.form_class = forms.DocumentIncomeForm
        if 'active_app' in request.session:
            return super(DocumentIncomeView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def form_valid(self, form):
        app = Application.objects.filter(id = self.request.session['app_id'])[0]
        if self.request.session['hasHouseholdBenefits'] == 'True':
            app.benefits_photo = form.cleaned_data['benefits_photo']
        else:
            app.income_photo = form.cleaned_data['income_photo']
        app.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = '/apply/documents-residence/'
        return context

class DocumentResidenceView(FormView):
    template_name = 'pathways/docs/upload-form.html'
    success_url = '/apply/confirmation/'

    def dispatch(self, request, *args, **kwargs):
        if self.request.session['rent_or_own'] == 'rent':
            self.form_class = forms.DocumentTenantForm
        else:
            self.form_class = forms.DocumentHomeownerForm
        if 'active_app' in request.session:
            return super(DocumentResidenceView, self).dispatch(request, *args, **kwargs)
        else:
            return redirect('pathways-home')

    def form_valid(self, form):
        app = Application.objects.filter(id = self.request.session['app_id'])[0]
        app.residence_photo = form.cleaned_data['residence_photo']
        app.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = '/apply/confirmation/'
        return context
        

class ConfirmationView(TemplateView):
    template_name = 'pathways/apply/confirmation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['confirm_timestamp'] = datetime.datetime.now().strftime("%m/%d/%Y")
        app = Application.objects.filter(id = self.request.session['app_id'])[0]
        context['hasHouseholdBenefits'] = app.hasHouseholdBenefits
        if app.income_photo:
            context['has_income_photo'] = True
        if app.benefits_photo:
            context['has_benefits_photo'] = True
        if app.residence_photo:
            context['has_residence_photo'] = True
        return context