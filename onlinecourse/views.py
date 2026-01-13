from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
import logging

from .models import (
    Course,
    Enrollment,
    Lesson,
    Question,
    Choice,
    Submission
)

# Logger
logger = logging.getLogger(__name__)


# =========================
# AUTHENTICATION VIEWS
# =========================

def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)

    username = request.POST['username']
    password = request.POST['psw']
    first_name = request.POST['firstname']
    last_name = request.POST['lastname']

    try:
        User.objects.get(username=username)
        context['message'] = "User already exists."
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    except User.DoesNotExist:
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        login(request, user)
        return redirect("onlinecourse:index")


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = "Invalid username or password."
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


# =========================
# HELPER FUNCTIONS
# =========================

def check_if_enrolled(user, course):
    if not user.is_authenticated:
        return False
    return Enrollment.objects.filter(user=user, course=course).exists()


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            submitted_answers.append(int(request.POST[key]))
    return submitted_answers


# =========================
# COURSE VIEWS
# =========================

class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            course.is_enrolled = check_if_enrolled(self.request.user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse('onlinecourse:course_details', args=(course.id,))
    )


# =========================
# EXAM SUBMISSION
# =========================

def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    enrollment = Enrollment.objects.get(user=user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)

    selected_choices = extract_answers(request)
    submission.choices.set(selected_choices)

    return HttpResponseRedirect(
        reverse(
            'onlinecourse:exam_result',
            args=(course_id, submission.id)
        )
    )


# =========================
# EXAM RESULT VIEW
# =========================

def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    selected_choices = submission.choices.all()
    questions = course.question_set.all()

    total_score = 0
    max_score = 0
    question_results = []

    for question in questions:
        correct_choices = question.choice_set.filter(is_correct=True)
        selected_for_question = selected_choices.filter(question=question)

        question_score = 0
        if set(correct_choices) == set(selected_for_question):
            question_score = question.grade

        total_score += question_score
        max_score += question.grade

        question_results.append({
            'question': question,
            'correct_choices': correct_choices,
            'selected_choices': selected_for_question,
            'score': question_score
        })

    context = {
        'course': course,
        'submission': submission,
        'total_score': total_score,
        'max_score': max_score,
        'question_results': question_results
    }

    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
