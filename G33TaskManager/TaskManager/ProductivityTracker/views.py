import os
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from TaskManagerPro.models import Task 

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' 

SCOPES = ['https://www.googleapis.com/auth/calendar']
CLIENT_SECRETS_FILE = os.path.join(settings.BASE_DIR, 'credentials.json')

def authorize_google(request):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://127.0.0.1:8000/productivity/oauth2callback/'
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    request.session['state'] = state
    return redirect(authorization_url)

def oauth2callback(request):
    state = request.session.get('state')
    if not state:
        return HttpResponse("Session expired. Please reauthorize.", status=400)

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri='http://127.0.0.1:8000/productivity/oauth2callback/'
    )
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    request.session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': SCOPES
    }
    return redirect('calendar_sync')

@login_required
def calendar_sync(request):
    creds_data = request.session.get('credentials')
    if not creds_data:
        return redirect('authorize_google')

    creds = Credentials(**creds_data)

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime').execute()

    events = events_result.get('items', [])

    return render(request, 'calendar.html', {'events': events})

@login_required
def export_task_to_calendar(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    creds_data = request.session.get('credentials')
    if not creds_data:
        return redirect('authorize_google')

    creds = Credentials(**creds_data)

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': task.title,
        'description': task.description,
        'start': {
            'dateTime': task.due_date.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': (task.due_date + datetime.timedelta(hours=1)).isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()

    return HttpResponse(f"Task exported to Google Calendar: <a href='{created_event.get('htmlLink')}' target='_blank'>View Event</a>")
