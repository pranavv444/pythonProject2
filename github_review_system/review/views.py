from xml.dom.expatbuilder import theDOMImplementation

import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from sympy.codegen import Print

from .models import GithubToken
import json
from django.views.decorators.csrf import csrf_exempt
import time
import google.generativeai as genai
import json
from typing import Optional
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
import os
from google.generativeai import configure

import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# Register view
def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        email = request.POST.get('email')

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match. Please try again.')
            return render(request, 'review/register.html')

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Please choose another one.')
            return render(request, 'review/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please use a different email.')
            return render(request, 'review/register.html')

        # Create a new user
        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.save()
            messages.success(request, 'Registration successful. Please log in.')
            print("user created")
            return redirect('login')  # Redirect to login page after registration
        except IntegrityError:
            messages.error(request, 'An error occurred during registration. Please try again.')
        except Exception as e:
            messages.error(request, f'Unexpected error: {e}')
            print("user not crated")
    return render(request, 'review/register.html')  # Render registration page


# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)  # Log in the user if authentication is successful
            messages.success(request, 'Login successful.')
            print("user login")
            return redirect('github_connect')  # Redirect to home or dashboard
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            print("user not login")

    return render(request, 'review/login.html')  # Render the login page if not POST


# Logout view
def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully.')
    return redirect('index')  # Redirect to login page after logout



def index(request):
    return render(request, 'review/home.html')


# This renders the HTML template with a button
@login_required
def github_connect(request):
    return render(request, 'review/connect.html')

# This view handles the actual OAuth redirect to GitHub
def github_redirect(request):
    client_id = settings.GITHUB_CLIENT_ID
    redirect_uri = 'http://localhost:8000/oauth/callback/'
    github_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}"
    return redirect(github_url)

# 2. OAuth Callback
def github_callback(request):
    code = request.GET.get('code')
    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET
    token_url = 'https://github.com/login/oauth/access_token'

    # Exchange code for access token
    response = requests.post(token_url, headers={'Accept': 'application/json'}, data={
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code
    })

    token_data = response.json()
    access_token = token_data.get('access_token')

    # Save token in the database
    GithubToken.objects.create(token=access_token)

    return render(request, 'review/success.html', {'token': access_token})


# 3. GitHub Webhook Handler
@csrf_exempt
def github_webhook(request):
    if request.method == 'POST':
        event = request.META.get('HTTP_X_GITHUB_EVENT')
        payload = request.body.decode('utf-8')

        if event == 'pull_request':
            process_pull_request(payload)

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'failure'}, status=400)


# 4. Process Pull Request Data
def process_pull_request(payload):
    payload = json.loads(payload)
    pr_data = payload.get('pull_request', {})
    pr_title = pr_data.get('title')
    pr_body = pr_data.get('body')

    # Call Hugging Face API for PR review
    review = call_huggingface_for_review(pr_title, pr_body)

    # Post review comment on GitHub
    post_review_comment(pr_data, review)


import requests
from django.conf import settings


# 4. Process Pull Request Data
def process_pull_request(payload):
    payload = json.loads(payload)
    pr_data = payload.get('pull_request', {})
    pr_title = pr_data.get('title')
    pr_body = pr_data.get('body')
    diff_url = pr_data.get('diff_url')  # URL for the diff of changes

    # Fetch the diff content (code changes)
    diff_content = fetch_diff_from_github(diff_url)

    # Call Hugging Face API for PR review
    review = call_huggingface_for_review(pr_title, pr_body, diff_content)

    # Post review comment on GitHub
    post_review_comment(pr_data, review)


def fetch_diff_from_github(diff_url):
    """
    Fetches the diff (code changes) from GitHub using the diff_url.
    """
    token = GithubToken.objects.first().token  # Get the saved token from the database
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff"  # Specific header to get the diff content
    }

    response = requests.get(diff_url, headers=headers)
    if response.status_code == 200:
        return response.text  # Return the raw diff text
    else:
        print(f"Error fetching diff from GitHub: {response.status_code}")
        return "Error: Unable to fetch diff."

# Fix: Add the third parameter `pr_diff` to the function definition
def call_huggingface_for_review(pr_title: str, pr_body: str, pr_diff: str) -> str:
    # Configure the Gemini model
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    if not pr_body or pr_body.lower() == 'none':
        pr_body = "The pull request does not contain a description. Please review based on the title."

    # Prepare the prompt, including the PR title, description, and diff content
    prompt = f"""
    You are an AI code reviewer. Please analyze the following pull request carefully:

    Title: {pr_title}
    Description: {pr_body}

    Code Changes (Diff):
    {pr_diff}

    Based on the information provided, suggest potential improvements, highlight any issues, and provide feedback about the changes made in the pull request. Focus on code quality, clarity, potential edge cases, and best practices.

    Respond with a concise and focused review.
    """

    # Print the prompt to check what is being sent to the API
    print("Prompt being sent to Gemini API:")
    print(json.dumps({'prompt': prompt}, indent=4))

    try:
        # Generate the review using Gemini
        response = model.generate_content(prompt)

        # Get the generated text from the response
        review_text = response.text.strip()

        # Optionally clean up any additional text that may be irrelevant
        review_text = clean_review_output(review_text)

        return review_text if review_text else "No review provided."

    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return f"Error: {str(e)}"

def clean_review_output(response_text):
    # Example cleaning logic to remove irrelevant
    # text
    filtered_text = response_text.split("See also:")[0]
    return filtered_text.strip()



# 6. Post Review as a Comment on GitHub
def post_review_comment(pr_data, review):
    pr_number = pr_data.get('number')
    repo_full_name = pr_data.get('base', {}).get('repo', {}).get('full_name')

    # Get token from database
    token = GithubToken.objects.first().token
    api_url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    data = {
        "body": review
    }

    response = requests.post(api_url, headers=headers, json=data)
    return response.status_code


def home(request):
    return render(request, 'index.html')

def tutorial(request):
    return render(request, 'review/tutorial.html')

@login_required
def code_review(request):
    return render(request, 'review/code_review.html')


@csrf_exempt
def analyze_code(request):
    if request.method == 'POST':
        code_text = request.POST.get('code_text')
        code_file = request.FILES.get('code_file')

        # Read code from the file if uploaded
        if code_file:
            code_text = code_file.read().decode('utf-8')

        # Escape special characters for API compatibility
        escaped_code_text = code_text.replace('\n', '\n').replace('\r', '\r')

        # Prepare the Gemini API request
        prompt = f"Analyze the following code for accuracy(give me the number score), optimization(give me the number score), and suggestions(give me the text data):\n\n{escaped_code_text}"
        ai_request = {
            "model": "gemini-1.5-flash",
            "prompt": prompt
        }

        try:
            # Send the request to the Gemini API
            model = genai.GenerativeModel(ai_request['model'])
            response = model.generate_content(ai_request['prompt'])

            # Extract only the "text" part from the response
            analysis_text = response.candidates[0].content.parts[0].text if response.candidates else "No analysis available"

            # Send only the "text" part back to the frontend
            return JsonResponse({"analysis": analysis_text})

        except Exception as e:
            print(f"Error in AI processing: {e}")
            return JsonResponse({"error": "An error occurred while processing the code."}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=405)