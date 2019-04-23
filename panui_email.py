# Requests stuff for getting information from the website and parsing it
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup as bs
from time import sleep

# Email stuff for sending emails
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Date stuff :P
from datetime import date
today = date.today()
ordinal = ['st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th', 'th',
           'th', 'th', 'th', 'th', 'th', 'th', 'th', 'th', 'th', 'th',
           'st', 'nd', 'rd', 'th', 'th', 'th', 'th', 'th', 'th', 'th',
           'st']

import csv
import sys
# Only send the panui to recipients on a school day
if today.weekday() > 4:
    sys.exit()

# Make sure that school website doesn't prevent us from scraping by setting a
# valid (or common) user agent.
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36'}
def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    def is_good_response(resp):
        content_type = resp.headers['Content-Type'].lower()
        return (resp.status_code == 200
                and content_type is not None
                and content_type.find('html') > -1)

    try:
        with closing(get(url, headers=headers, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            else:
                return None

    except RequestException as e:
        # There's been an error in the request - maybe the raspberry pi's internet is down, or the website's down?
        print(e)
        return None

# Don't change to https :)
raw_html = simple_get("http://www.rutherford.school.nz/daily-panui/")
html = bs(raw_html, 'html.parser')
print("got site")

# Parse the recieved site and extract all the notices from it
class Notice():
    def __init__(self, title, link, date, excerpt):
        self.title = title
        self.link = link
        self.date = date
        self.day = int(self.date.split("/")[0])
        self.excerpt = excerpt

notices = []
raw_notices = html.find_all(class_="vcex-blog-entry-details")
for notice in raw_notices:
    notices.append( Notice(
        notice.find(class_="vcex-blog-entry-title").contents[0].contents[0],
        notice.find(class_="vcex-blog-entry-title").find("a").get('href'),
        notice.find(class_="vcex-blog-entry-date").contents[0],
        notice.find(class_="vcex-blog-entry-excerpt").decode_contents()
        )
    )
# Don't filer out all the notices by their date cause Rutherford sucks
#notices = [notice for notice in notices if notice.day == today.day]
if len(notices) == 0:
    sys.exit()
print(f"got {len(notices)} noticies")

# Generate the html message to be sent
def generate_message(recipient):
    text = "Ew get a more up-to-date email client that supports html, jeez."
    html = f"<html><body><h1 style=\"margin-bottom:0px\">Kia Ora {recipient.name},</h1>\
    Here is the Rutherford College Daily Panui for {today.strftime('%A')} {today.day}{ordinal[today.day-1]} of {today.strftime('%B, %Y')}:"
    html += "<table>"
    for notice in notices:
        html += "<tr><td style=\"padding: 2em 0 0 0\"><table><tr><td style=\"border:1px solid black; border-radius:5px\">"
        html += f"<span style=\"padding: 0.4em 0 0 0; display:block; font-size:1.5em; font-weight:bold\">{notice.title}</span>"
        html += "<span style=\"display:block; margin:0\">" + notice.date + "</span>"
        html += notice.excerpt
        html += f"<a href=\"{notice.link}\" style=\"padding: 0 0 1em 0; font-size:0.83em\">read more ></a>"
        html += "</td></tr></table></tr></td>"

    html +="</table>"
    html += "<h6>Wish to Unsubscribe from these emails? Click <a href=\"https://bit.ly/IqT6zt\">here</a>.</h6></body></html>"

    # Make the neccecary message objects for sending the email (not strictly neccesssary but we have to if we want to send emails not-shittily)
    message = MIMEMultipart("alternative")
    message["Subject"] = today.strftime("Rutherford Panui, %d/%m/%y")
    message["From"] = program_email
    message["To"] = reciever_email
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)
    return message.as_string()

# Get the email and password for the program
program_email = "stoofinthepoofin@gmail.com"
with open("password.txt") as file:
    password = file.read()

print("sending to recipients...")

context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(program_email, password)

    # Simplifies storing of and interaction with recipients
    class Recipient:
        def __init__(self, name, email):
            self.name = name
            self.email = email
    # I made this into a fuction because I need to do it twice, and once pay attention to the "#" while the other time ignore it
    def get_mailing_list(all_people=False):
        output = []
        with open("mailing_list.csv") as file:
            reader = csv.reader(file)
            next(reader)
            for name, reciever_email in reader:
                if name[0] == "#":
                    if all_people:
                        output.append(Recipient(name[1:], reciever_email))
                    else:
                        continue
                else:
                    output.append(Recipient(name, reciever_email))
        return output
    mailing_list = get_mailing_list()

    # If an email was manually supplied, find it's corresponding name in mailing_list.csv (if it has one, otherwise just use email twice)
    # Otherwise, just use the mailing list itself
    emails = []
    if len(sys.argv) > 1:
        for reciever_email in sys.argv[1:]:
            recipient = [x for x in get_mailing_list(True) if x.email == reciever_email]
            if recipient != []:
                emails.append(recipient[0])
            else:
                emails.append(Recipient(reciever_email, reciever_email))
    else:
        emails = mailing_list

    # Send the email!
    for recipient in emails:
            print("-", recipient.name, recipient.email)
            server.sendmail(program_email, recipient.email, generate_message(recipient))

print("sent!")



