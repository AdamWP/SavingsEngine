# -*- coding: utf-8 -*-

from __main__ import Session_main
from __main__ import models

import sys
import os
import time
import datetime
import uuid

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from settings import S3_ENDPOINT
from settings import PRODUCT_IMAGE_BUCKET_NAME
from settings import STORE_IMAGE_BUCKET

from settings import SMTP_SERVER
from settings import SMTP_PORT
from settings import SMTP_LOGIN
from settings import SMTP_PASSWORD
from settings import APP_VERSION_iOS
from settings import APP_VERSION_ANDROID


def email_crash_report(endpoint, e):
    try:
        print('CRASH EMAIL REPORT')
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🤮 TopSavings API ERROR 🤮'
        msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Team'

        text = "There was an error on the API server 1. Endpoint " + endpoint + ". Error " + str(e) + ". Check the logs"

        part1 = MIMEText(text, 'plain')

        msg.attach(part1)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login("mailer@linkclicks.com", SMTP_PASSWORD)

        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
        server.quit()
    except Exception as e:
        print(e)
        return False


def email_alert(alert_subject, alert_text, alert_html, *positional_parameters, **keyword_parameters):

    print('EMAIL ALERT START')
    if 'alert_type' in keyword_parameters:
        alert_type = keyword_parameters['alert_type']
    else:
        alert_type = None

    if 'user_id' in keyword_parameters:
        user_id = keyword_parameters['user_id']
    else:
        user_id = None

    if alert_subject is not None and (alert_text is not None or alert_html is not None):
        print('EMAIL ALERT')
        if alert_subject == 'execution_time':
            execution_time_issue = True
            alert_subject = '⌛ ' + str(alert_subject)
            print('execution time issue')
        else:
            execution_time_issue = False

        msg = MIMEMultipart('alternative')
        msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Team'

        if alert_text is not None:
            part1 = MIMEText(alert_text, 'plain')
            msg.attach(part1)

        if alert_html is not None:
            part2 = MIMEText(alert_html, 'html')
            msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        if alert_type == 'return_user':
            user_id = keyword_parameters['user_id']
            if user_id == '1' or user_id == '3' or user_id == '5' or user_id == '189' or user_id == '210':
                return None
            token = str(uuid.uuid4())

            # the app hits multiple endpoints at the same time, so we set up a queue to prevent getting multiple alerts
            sql_query = 'insert into alert_queue (token, user_id) values ("' + token + '","' + str(user_id) + '")'

            session_main = Session_main()
            session_main.execute(sql_query)
            session_main.commit()
            #session_main.close()

            time.sleep(60)

            sql_query = 'select *, (select count(*) from api_activity where user_id = "' + str(user_id) + '" and endpoint = "/startup_check") as startup_count, (select gps_lat from api_activity where user_id = "' + str(user_id) + '" and gps_lat is not null order by id desc limit 1) as gps_lat, (select gps_lng from api_activity where user_id = "' + str(user_id) + '" and gps_lng is not null order by id desc limit 1) as gps_lng from alert_queue where user_id = "' + str(user_id) + '" order by id limit 1'

            queue_info = session_main.execute(sql_query)
            session_main.close()

            queue_info = list(queue_info)

            if queue_info:
                for row in queue_info:
                    if row.token is not None and row.token != '':
                        queue_token = row.token
                        gps_lat = row.gps_lat
                        gps_lng = row.gps_lng
                        startup_count = row.startup_count

                        alert_text = alert_text + ' They have used the app ' + str(startup_count) + ' times.'

                        if gps_lat == '45.414926' and gps_lng == '-75.696562':
                            alert_subject = alert_subject + ' GPS PROBLEM'

                        if queue_token == token:
                            if gps_lat is not None and gps_lng is not None:
                                alert_text = alert_text + '  https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)
                            part1 = MIMEText(alert_text, 'plain')
                            msg.attach(part1)

                            msg['Subject'] = str(alert_subject)

                            server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
                            server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())
                            server.quit()
                            sql_query = 'delete from alert_queue where user_id = "' + str(user_id) + '"'
                            session_main.execute(sql_query)
                            session_main.commit()
                            session_main.close()

        elif alert_type == 'execution_time':

            msg['Subject'] = str(alert_subject)
            server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
            server.quit()
        elif alert_type == 'new_user' or alert_type == 'return_user' or alert_type == 'deal_shared' or alert_type == 'share_opened' or alert_type == 'bad_gps':

            time.sleep(60)
            session_main = Session_main()

            if user_id is not None:
                user = session_main.query(models.user).filter(models.user.id == user_id).first()

                if user:
                    app_version = user.app_version
                    if app_version is None:
                        app_version = ''

                    os_type = user.OS

                    if os_type is not None and app_version is not None:
                        if os_type == 'Android':
                            alert_subject = alert_subject.replace(':OS:', '🤖[' + str(app_version) + '/' + str(APP_VERSION_ANDROID) + ']')
                        elif os_type == 'iOS':
                            alert_subject = alert_subject.replace(':OS:', '[' + str(app_version) + '/' + str(APP_VERSION_iOS) + ']')
                        else:

                            alert_subject = alert_subject.replace(':OS:', 'Invalid OS Type ')

                        if os_type != '' and os_type is not None:
                            alert_subject = alert_subject.replace('TopSavings', str(os_type))

                            alert_text = alert_text.replace(':OS:', str(os_type))

                        msg['Subject'] = str(alert_subject)

                    part1 = MIMEText(alert_text, 'plain')
                    msg.attach(part1)
                else:
                    alert_subject = alert_subject.replace(':OS:', 'Unknown OS')
                    msg['Subject'] = str(alert_subject)
            else:
                alert_subject = alert_subject.replace(':OS:', 'Unknown OS')
                msg['Subject'] = str(alert_subject)

            server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())
            server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
            server.quit()

        else:
            msg['Subject'] = str(alert_subject)
            server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
            server.quit()

    else:
        return False


html_start = """

                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:v="urn:schemas-microsoft-com:vml">
<head>
<!--[if gte mso 9]><xml><o:OfficeDocumentSettings><o:AllowPNG/><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
<meta content="width=device-width" name="viewport"/>
<!--[if !mso]><!-->
<meta content="IE=edge" http-equiv="X-UA-Compatible"/>
<!--<![endif]-->
<title></title>
<!--[if !mso]><!-->
<!--<![endif]-->
<style type="text/css">
		body {
			margin: 0;
			padding: 0;
		}

		table,
		td,
		tr {
			vertical-align: top;
			border-collapse: collapse;
		}

		* {
			line-height: inherit;
		}

		a[x-apple-data-detectors=true] {
			color: inherit !important;
			text-decoration: none !important;
		}
	</style>
<style id="media-query" type="text/css">
		@media (max-width: 500px) {

			.block-grid,
			.col {
				min-width: 320px !important;
				max-width: 100% !important;
				display: block !important;
			}

			.block-grid {
				width: 100% !important;
			}

			.col {
				width: 100% !important;
			}

			.col>div {
				margin: 0 auto;
			}

			img.fullwidth,
			img.fullwidthOnMobile {
				max-width: 100% !important;
			}

			.no-stack .col {
				min-width: 0 !important;
				display: table-cell !important;
			}

			.no-stack.two-up .col {
				width: 50% !important;
			}

			.no-stack .col.num4 {
				width: 33% !important;
			}

			.no-stack .col.num8 {
				width: 66% !important;
			}

			.no-stack .col.num4 {
				width: 33% !important;
			}

			.no-stack .col.num3 {
				width: 25% !important;
			}

			.no-stack .col.num6 {
				width: 50% !important;
			}

			.no-stack .col.num9 {
				width: 75% !important;
			}

			.video-block {
				max-width: none !important;
			}

			.mobile_hide {
				min-height: 0px;
				max-height: 0px;
				max-width: 0px;
				display: none;
				overflow: hidden;
				font-size: 0px;
			}

			.desktop_hide {
				display: block !important;
				max-height: none !important;
			}
		}
	</style>
</head>
<body class="clean-body" style="margin: 0; padding: 0; -webkit-text-size-adjust: 100%; background-color: #f5d813;">
<!--[if IE]><div class="ie-browser"><![endif]-->
<table bgcolor="#f5d813" cellpadding="0" cellspacing="0" class="nl-container" role="presentation" style="table-layout: fixed; vertical-align: top; min-width: 320px; Margin: 0 auto; border-spacing: 0; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; background-color: #f5d813; width: 100%;" valign="top" width="100%">
<tbody>
<tr style="vertical-align: top;" valign="top">
<td style="word-break: break-word; vertical-align: top;" valign="top">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" style="background-color:#f5d813"><![endif]-->
<div style="background-color:transparent;">
<div class="block-grid" style="Margin: 0 auto; min-width: 320px; max-width: 480px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; background-color: transparent;">
<div style="border-collapse: collapse;display: table;width: 100%;background-color:transparent;">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;"><tr><td align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:480px"><tr class="layout-full-width" style="background-color:transparent"><![endif]-->
<!--[if (mso)|(IE)]><td align="center" width="480" style="background-color:transparent;width:480px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num12" style="min-width: 320px; max-width: 480px; display: table-cell; vertical-align: top; width: 480px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<div align="left" class="img-container left fixedwidth" style="padding-right: 10px;padding-left: 10px;">
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr style="line-height:0px"><td style="padding-right: 10px;padding-left: 10px;" align="left"><![endif]-->
<div style="font-size:1px;line-height:10px"> </div><img alt="Image" border="0" class="left fixedwidth" src="https://www.TopSavings.com/static/email/img/logo.png" style="text-decoration: none; -ms-interpolation-mode: bicubic; border: 0; height: auto; width: 100%; max-width: 168px; display: block;" title="Image" width="168"/>
<div style="font-size:1px;line-height:10px"> </div>
<!--[if mso]></td></tr></table><![endif]-->
</div>
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td></tr></table></td></tr></table><![endif]-->
</div>
</div>
</div>
<div style="background-color:transparent;">
<div class="block-grid" style="Margin: 0 auto; min-width: 320px; max-width: 480px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; background-color: transparent;">
<div style="border-collapse: collapse;display: table;width: 100%;background-color:transparent;">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;"><tr><td align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:480px"><tr class="layout-full-width" style="background-color:transparent"><![endif]-->
<!--[if (mso)|(IE)]><td align="center" width="480" style="background-color:transparent;width:480px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num12" style="min-width: 320px; max-width: 480px; display: table-cell; vertical-align: top; width: 480px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 10px; padding-left: 10px; padding-top: 10px; padding-bottom: 10px; font-family: Arial, sans-serif"><![endif]-->
<div style="color:#555555;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;line-height:1.2;padding-top:10px;padding-right:10px;padding-bottom:10px;padding-left:10px;">
<div style="font-size: 14px; line-height: 1.2; color: #555555; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; mso-line-height-alt: 17px;">
<p style="font-size: 24px; line-height: 1.2; word-break: break-word; mso-line-height-alt: 29px; margin: 0;"><span style="font-size: 24px; color: #000000;"><strong>user {user_id}:</strong></span></p>
</div>
</div>
<!--[if mso]></td></tr></table><![endif]-->
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td></tr></table></td></tr></table><![endif]-->
</div>
</div>
</div>



"""


activity_icon_html = """

                <div style="background-color:transparent;">
<div class="block-grid mixed-two-up no-stack" style="Margin: 0 auto; min-width: 320px; max-width: 480px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; background-color: transparent;">
<div style="border-collapse: collapse;display: table;width: 100%;background-color:transparent;">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;"><tr><td align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:480px"><tr class="layout-full-width" style="background-color:transparent"><![endif]-->
<!--[if (mso)|(IE)]><td align="center" width="120" style="background-color:transparent;width:120px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num3" style="display: table-cell; vertical-align: top; max-width: 320px; min-width: 120px; width: 120px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<div align="center" class="img-container center fixedwidth" style="padding-right: 10px;padding-left: 10px;">
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr style="line-height:0px"><td style="padding-right: 10px;padding-left: 10px;" align="center"><![endif]-->
<div style="font-size:1px;line-height:10px"> </div><img align="center" alt="Image" border="0" class="center fixedwidth" src="{activity_image}" style="text-decoration: none; -ms-interpolation-mode: bicubic; border: 0; height: auto; width: 100%; max-width: 36px; display: block;" title="Image" width="36"/>
<div style="font-size:1px;line-height:10px"> </div>
<!--[if mso]></td></tr></table><![endif]-->
</div>
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td><td align="center" width="360" style="background-color:transparent;width:360px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num9" style="display: table-cell; vertical-align: top; min-width: 320px; max-width: 360px; width: 360px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 10px; padding-left: 10px; padding-top: 10px; padding-bottom: 10px; font-family: Arial, sans-serif"><![endif]-->
<div style="color:#555555;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;line-height:1.2;padding-top:10px;padding-right:10px;padding-bottom:10px;padding-left:10px;">
<div style="font-size: 14px; line-height: 1.2; color: #555555; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; mso-line-height-alt: 17px;">
<p style="font-size: 18px; line-height: 1.2; word-break: break-word; mso-line-height-alt: 22px; margin: 0;"><span style="color: #000000; font-size: 18px;">{activity_text}</span></p>
</div>
</div>
<!--[if mso]></td></tr></table><![endif]-->
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td></tr></table></td></tr></table><![endif]-->
</div>
</div>
</div>

"""


activity_product_html = """

                        <div style="background-color:transparent;">
<div class="block-grid mixed-two-up no-stack" style="Margin: 0 auto; min-width: 320px; max-width: 480px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; background-color: transparent;">
<div style="border-collapse: collapse;display: table;width: 100%;background-color:transparent;">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;"><tr><td align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:480px"><tr class="layout-full-width" style="background-color:transparent"><![endif]-->
<!--[if (mso)|(IE)]><td align="center" width="120" style="background-color:transparent;width:120px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num3" style="display: table-cell; vertical-align: top; max-width: 320px; min-width: 120px; width: 120px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<div align="center" class="img-container center fixedwidth" style="padding-right: 10px;padding-left: 10px;">
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr style="line-height:0px"><td style="padding-right: 10px;padding-left: 10px;" align="center"><![endif]-->
<div style="font-size:1px;line-height:10px"> </div><img align="center" alt="Image" border="0" class="center fixedwidth" src="{activity_image}" style="text-decoration: none; -ms-interpolation-mode: bicubic; border: 0; height: auto; width: 100%; max-width: 72px; display: block;" title="Image" width="72"/>
<div style="font-size:1px;line-height:10px"> </div>
<!--[if mso]></td></tr></table><![endif]-->
</div>
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td><td align="center" width="360" style="background-color:transparent;width:360px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num9" style="display: table-cell; vertical-align: top; min-width: 320px; max-width: 360px; width: 360px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<!--[if mso]><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 10px; padding-left: 10px; padding-top: 10px; padding-bottom: 10px; font-family: Arial, sans-serif"><![endif]-->
<div style="color:#555555;font-family:Arial, Helvetica Neue, Helvetica, sans-serif;line-height:1.2;padding-top:10px;padding-right:10px;padding-bottom:10px;padding-left:10px;">
<div style="line-height: 1.2; font-size: 12px; color: #555555; font-family: Arial, Helvetica Neue, Helvetica, sans-serif; mso-line-height-alt: 14px;">
<p style="text-align: left; line-height: 1.2; word-break: break-word; font-size: 18px; mso-line-height-alt: 22px; margin: 0;"><span style="font-size: 18px; color: #000000;">{activity_text}</span></p>
</div>
</div>
<!--[if mso]></td></tr></table><![endif]-->
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td></tr></table></td></tr></table><![endif]-->
</div>
</div>
</div>

"""


html_line = """
                <div style="background-color:transparent;">
<div class="block-grid" style="Margin: 0 auto; min-width: 320px; max-width: 480px; overflow-wrap: break-word; word-wrap: break-word; word-break: break-word; background-color: transparent;">
<div style="border-collapse: collapse;display: table;width: 100%;background-color:transparent;">
<!--[if (mso)|(IE)]><table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;"><tr><td align="center"><table cellpadding="0" cellspacing="0" border="0" style="width:480px"><tr class="layout-full-width" style="background-color:transparent"><![endif]-->
<!--[if (mso)|(IE)]><td align="center" width="480" style="background-color:transparent;width:480px; border-top: 0px solid transparent; border-left: 0px solid transparent; border-bottom: 0px solid transparent; border-right: 0px solid transparent;" valign="top"><table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding-right: 0px; padding-left: 0px; padding-top:5px; padding-bottom:5px;"><![endif]-->
<div class="col num12" style="min-width: 320px; max-width: 480px; display: table-cell; vertical-align: top; width: 480px;">
<div style="width:100% !important;">
<!--[if (!mso)&(!IE)]><!-->
<div style="border-top:0px solid transparent; border-left:0px solid transparent; border-bottom:0px solid transparent; border-right:0px solid transparent; padding-top:5px; padding-bottom:5px; padding-right: 0px; padding-left: 0px;">
<!--<![endif]-->
<table border="0" cellpadding="0" cellspacing="0" class="divider" role="presentation" style="table-layout: fixed; vertical-align: top; border-spacing: 0; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; min-width: 100%; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%;" valign="top" width="100%">
<tbody>
<tr style="vertical-align: top;" valign="top">
<td class="divider_inner" style="word-break: break-word; vertical-align: top; min-width: 100%; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%; padding-top: 10px; padding-right: 10px; padding-bottom: 10px; padding-left: 10px;" valign="top">
<table align="center" border="0" cellpadding="0" cellspacing="0" class="divider_content" role="presentation" style="table-layout: fixed; vertical-align: top; border-spacing: 0; border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; border-top: 1px solid #BBBBBB; width: 100%;" valign="top" width="100%">
<tbody>
<tr style="vertical-align: top;" valign="top">
<td style="word-break: break-word; vertical-align: top; -ms-text-size-adjust: 100%; -webkit-text-size-adjust: 100%;" valign="top"><span></span></td>
</tr>
</tbody>
</table>
</td>
</tr>
</tbody>
</table>
<!--[if (!mso)&(!IE)]><!-->
</div>
<!--<![endif]-->
</div>
</div>
<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
<!--[if (mso)|(IE)]></td></tr></table></td></tr></table><![endif]-->
</div>
</div>
</div>
"""


html_end = """

<!--[if (mso)|(IE)]></td></tr></table><![endif]-->
</td>
</tr>
</tbody>
</table>
<!--[if (IE)]></div><![endif]-->
</body>
</html>

"""


def session_time(user_id, start_date_time, session_inactive_time):
    try:
        time.sleep(10)

        live_session = True
        session_main = Session_main()

        sleep_time = session_inactive_time

        while live_session is True:

            str_sql = 'select date_time from api_activity where user_id = ' + str(user_id) + ' and (endpoint not like "%check_in") order by id desc limit 1'

            item_info = session_main.execute(str_sql)

            session_main.close()

            for row in item_info:
                last_date_time = row.date_time


                d1 = start_date_time
                d2 = last_date_time
                d3 = datetime.datetime.now()

                d1_ts = time.mktime(d1.timetuple())
                d2_ts = time.mktime(d2.timetuple())
                d3_ts = time.mktime(d3.timetuple())

                session_time = int(d2_ts - d1_ts)

                if int(d3_ts - d2_ts) >= session_inactive_time:

                    return session_time

                sleep_time = session_inactive_time - d3_ts + d2_ts

            if sleep_time > 0:
                print('Wait')
                time.sleep(sleep_time)

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        # email_report('get_price', e)


def session_alert(user_id, start_date_time, os_type, user_type, away_time, deals_shared_id, user_share_code):

    chain_visited = None

    try:

        start_date_time_b = start_date_time - datetime.timedelta(minutes=1)
        session_main = Session_main()

        user_session_time = session_time(user_id, start_date_time, 300)

        if user_session_time < 1:
            user_session_time = 0

        html = html_start

        html = html.replace('{user_id}', str(user_id))

        if deals_shared_id is not None:
            activity_html = activity_icon_html.replace('{activity_image}',
                                                       'https://www.topsavings.com/static/email/img/new_user.png')
            activity_html = activity_html.replace('{activity_text}',
                                                  'referred: https://www.topsavings.com/deals/deal_' + str(deals_shared_id) + ' \r\n  \r\n ')
            html = html + activity_html

        elif user_share_code != False and user_share_code is not None:
            activity_html = activity_icon_html.replace('{activity_image}',
                                                       'https://www.topsavings.com/static/email/img/new_user.png')
            activity_html = activity_html.replace('{activity_text}', 'referred from ' + str(user_share_code))

        elif 'New' in user_type:
            activity_html = activity_icon_html.replace('{activity_image}',
                                                       'https://www.topsavings.com/static/email/img/new_user.png')
            activity_html = activity_html.replace('{activity_text}', 'New User')

        #elif 'Skipped' in user_type:
        #    activity_html = activity_icon_html.replace('{activity_image}','https://www.topsavings.com/static/email/img/new_user.png')
        #    activity_html = activity_html.replace('{activity_text}', 'Skipped User')

        #    html = html + activity_html

        str_sql = 'select * from api_activity where user_id = ' + str(user_id) + ' and date_time >= "' + str(start_date_time) + '" order by id '

        str_sql = 'select *,(select chain from stores where st_distance_sphere(stores.pt, Point(api_activity.gps_lng, api_activity.gps_lat)) < 75 order by (st_distance_sphere(stores.pt, Point(api_activity.gps_lng, api_activity.gps_lat))) limit 1 ) as chain, (select st_distance_sphere(Point(-75.697768, 45.416136), Point(api_activity.gps_lng, api_activity.gps_lat)))AS distance_ottawa, (select query from search where search.id = api_activity.search_id and query is not null limit 1) as query, (select brand from item_info where prod_id = api_activity.prod_id and prod_id is not null and disabled is null order by id desc limit 1) as brand, (select prod_name from item_info where prod_id = api_activity.prod_id and prod_id is not null and disabled is null order by id desc limit 1) as prod_name, (select image from item_info where prod_id = api_activity.prod_id and prod_id is not null and disabled is null order by id desc limit 1) as image from api_activity where user_id = ' + str(user_id) + ' and date_time >= "' + str(start_date_time_b) + '" and (endpoint like "%/change_range" or endpoint like "%/deals" or endpoint like "%/get_share" or endpoint like "%/new_user" or endpoint like "%/report_price" or endpoint like "%/scan" or endpoint like "%/search" or endpoint like "%/set_checked" or endpoint like "%/set_store_enabled" or endpoint like "%/tap_deal" or endpoint like "%/tap_tab" or endpoint like "%/onboard_skipped_user" or endpoint like "%/set_shopping_list" or endpoint like "%/skip_login" or endpoint like "%/startup_check") order by id '

        activity_info = session_main.execute(str_sql)

        flow = ''
        gps_lat = None
        gps_lng = None

        for row in activity_info:

            endpoint = row.endpoint

            flow_end = row.date_time

            if flow == '':
                flow_start = flow_end

            query = row.query

            chain = row.chain
            if chain is not None:
                chain_visited = chain

            brand = row.brand
            prod_name = row.prod_name
            prod_id = row.prod_id
            page = row.page
            tab = row.tab
            generic_name = row.generic_name
            image = row.image

            if row.gps_lat is not None:
                gps_lat = row.gps_lat

            if row.gps_lng is not None:
                gps_lng = row.gps_lng

            if image is None:
                image = S3_ENDPOINT + '/' + STORE_IMAGE_BUCKET + '/no_image_grocery_sm.png'
            else:
                image = S3_ENDPOINT + '/' + PRODUCT_IMAGE_BUCKET_NAME + '/sm_new/' + str(image)

            if prod_name is None:
                prod_name = prod_id

            if prod_name is not None and brand is not None and brand not in prod_name:
                prod_name = brand + ' ' + prod_name

            if generic_name is not None:
                prod_name = generic_name

            t1 = time.mktime(flow_start.timetuple())
            t2 = time.mktime(flow_end.timetuple())
            tdelta = t2 - t1

            flow_start = flow_end

            if tdelta > 0:
                flow = flow + str(tdelta) + ' seconds  \r\n '

                if int(tdelta) > 59:
                    activity_minutes = tdelta / 60
                    activity_minutes = int(activity_minutes)
                    activity_seconds = tdelta - (activity_minutes * 60)

                    activity_time = str(activity_minutes) + ':' + str(activity_seconds)
                else:
                    activity_time = str(tdelta) + ' seconds'

                html_time = activity_icon_html
                html_time = html_time.replace('{activity_text}', activity_time)
                html_time = html_time.replace('{activity_image}',
                                              'https://www.topsavings.com/static/email/img/clock.png')

                html = html + html_time

            flow = flow + str(endpoint) + ' \r\n '

            if '/change_range' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/range.png')
                activity_html = activity_html.replace('{activity_text}', 'changed range')
            elif '/deals' in endpoint and page is not None and page > 1:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/deals.png')
                activity_html = activity_html.replace('{activity_text}', 'Page: ' + str(page))
            elif '/get_share' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/share.png')
                activity_html = activity_html.replace('{activity_text}', str(prod_name))
            elif '/new_user' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/new_user.png')
                activity_html = activity_html.replace('{activity_text}', 'New  User')
            # elif '/profile' in endpoint or '/settings' in endpoint:
            #    activity_html = activity_icon_html.replace('{activity_image}', 'https://www.topsavings.com/static/email/img/profile.png')
            #    activity_html = activity_html.replace('{activity_text}', str(endpoint))
            elif '/report_price' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/report.png')
                activity_html = activity_html.replace('{activity_text}', str(endpoint))
            elif '/scan' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/scan.png')
                activity_html = activity_html.replace('{activity_text}', str(prod_name))
            elif '/search' in endpoint:

                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/search.png')
                activity_html = activity_html.replace('{activity_text}', str(query) + ' :page ' + str(page))

            elif '/set_checked' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/check.png')
                activity_html = activity_html.replace('{activity_text}', str(prod_name))

            elif '/set_store_enabled' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/set_store.png')
                activity_html = activity_html.replace('{activity_text}', 'Store Enabled/Disabled')
            elif '/tap_deal' in endpoint:
                activity_html = activity_product_html.replace('{activity_image}', image)
                activity_html = activity_html.replace('{activity_text}', str(prod_name))
            elif '/tap_tab' in endpoint:

                if tab == 'deals':
                    html = html + html_line
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/deals.png')
                elif tab == 'shopping_list':
                    html = html + html_line
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/shopping_list.png')
                elif tab == 'search':
                    html = html + html_line
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/search.png')
                elif tab == 'settings':
                    html = html + html_line
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/profile.png')
                elif tab == 'calculate':
                    html = html + html_line
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/calculate.png')
                elif tab == 'calculate_1':

                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/calculate_1.png')
                    activity_html = activity_html.replace('{activity_text}', 'calculate 1 store')
                elif tab == 'calculate_2':

                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/calculate_2.png')
                    activity_html = activity_html.replace('{activity_text}', 'calculate 2 stores')
                elif tab == 'calculate_3':

                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/calculate_3.png')
                    activity_html = activity_html.replace('{activity_text}', 'calculate 3 stores')
                elif tab == 'calculate_all':

                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/calculate_all.png')
                    activity_html = activity_html.replace('{activity_text}', 'calculate all stores')
                elif tab == 'price_check':
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/scan.png')

                else:
                    activity_html = activity_icon_html.replace('{activity_image}',
                                                               'https://www.topsavings.com/static/email/img/none.gif')

                activity_html = activity_html.replace('{activity_text}', tab)
            elif '/onboard_skipped_user' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/onboard_skipped.png')
                activity_html = activity_html.replace('{activity_text}', 'onboard skipped user')

            elif '/set_shopping_list' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/add_to_list.png')
                activity_html = activity_html.replace('{activity_text}', str(prod_name))

            elif '/skip_login' in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/new_user.png')
                activity_html = activity_html.replace('{activity_text}', 'skipped user')

            elif '/deals' not in endpoint:
                activity_html = activity_icon_html.replace('{activity_image}',
                                                           'https://www.topsavings.com/static/email/img/none.gif')
                activity_html = activity_html.replace('{activity_text}', endpoint)
            else:
                #    activity_html = activity_icon_html.replace('{activity_image}', 'https://www.topsavings.com/static/email/img/none.gif')
                #    activity_html = activity_html.replace('{activity_text}', endpoint)
                activity_html = ''

            html = html + activity_html

        if gps_lat is not None and gps_lng is not None:

            map_gps = 'https://www.google.com/maps/place/' + str(gps_lat) + ',' + str(gps_lng)

            html_gps = activity_icon_html.replace('{activity_text}', map_gps)
            html_gps = html_gps.replace('{activity_image}', 'https://www.topsavings.com/static/email/img/none.gif')

            html = html + html_line + html_gps

        html = html + html_end

        text = flow

        user = session_main.query(models.user).filter(models.user.id == user_id).first()

        if user:
            os_type = user.OS
            app_version = user.app_version
            if app_version is None:
                app_version = ''
        else:
            os_type = 'Unknown OS'
            app_version = ''

        if os_type == 'iOS':
            os_subject = '[' + str(app_version) + '/' + str(APP_VERSION_iOS) + ']'
        elif os_type == 'Android':
            os_subject = '🤖[' + str(app_version) + '/' + str(APP_VERSION_ANDROID) + ']'
        else:
            os_subject = 'UNKNOWN 1'

        subject = ''

        if user_session_time < 30:
            print('Short Session')
            subject = '🚨 ' + str(user_session_time) + 's ' + subject + ' '

        if chain_visited is not None:
            print('IN STORE USER ' + str(chain_visited))
            subject = '🏬 ' + chain_visited + subject + ' '

        if int(user_session_time) > 59:
            session_minutes = user_session_time / 60
            session_minutes = int(session_minutes)
            session_seconds = user_session_time - (session_minutes * 60)
            if session_seconds < 10:
                session_seconds = '0' + str(session_seconds)

            session_time_subject = str(session_minutes) + ':' + str(session_seconds)
        else:
            session_time_subject = str(user_session_time) + ' seconds'

        if 'notification' in user_type:
            subject = subject + '*️⃣ 🔙🔔' + os_subject

        elif 'Return User' in user_type:
            subject = subject + '*️⃣ 🔙' + os_subject

        elif ('New' in user_type or 'Skipped' in user_type) and (user_share_code is None and deals_shared_id is None):
            subject = subject + '🌱' + os_subject

        elif ('New' in user_type or 'Skipped' in user_type) and (user_share_code == 'website' and deals_shared_id is None):

            subject = subject + '🌿' + os_subject

        elif 'New' in user_type or 'Skipped' in user_type:
            subject = subject + '❇️' + os_subject

        subject = subject + ' ' + user_type

        if away_time is not None:
            subject = subject + ' ' + away_time

        subject = subject + ' ' + session_time_subject

        if deals_shared_id is not None:
            subject = subject + ' (via share)'

        if user_share_code is not None and deals_shared_id is None:
            subject = subject + ' (via ' + str(user_share_code) + ')'

        msg = MIMEMultipart('alternative')
        msg['From'] = 'TopSavings API <mailer@TopSavings.com>'
        msg['To'] = 'TopSavings Team'

        part1 = MIMEText(text, 'plain')
        msg.attach(part1)

        part2 = MIMEText(html, 'html')
        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        msg['Subject'] = subject
        server.sendmail("mailer@TopSavings.com", "adam@topsavings.com", msg.as_string())
        server.sendmail("mailer@TopSavings.com", "steve@topsavings.com", msg.as_string())

        server.quit()

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)


def send_welcome_email(user_id, email_address, confirm_key, unsub_key):

    try:

        session_main = Session_main()

        session_start = datetime.datetime.now()

        user_session_time = session_time(user_id, session_start, 600)

        if user_session_time < 30:
            print('Send short session email')
            email_id = 3
            str_sql = 'select * from emails where id = 3 limit 1'
            email_info = session_main.execute(str_sql)

            for row in email_info:
                text = row.text
                html = row.html
        else:

            str_sql = 'select * from shopping_list where user_id = ' + str(user_id)
            list_info = session_main.execute(str_sql)
            session_main.close()

            list_info = list(list_info)

            generic_count = 0 + sum(1 for x in list_info if x.generic_name is not None)

            if len(list_info) < 5:
                print('Send no shopping list email')

                email_id = 4
                str_sql = 'select * from emails where id = 4 limit 1'
                email_info = session_main.execute(str_sql)

                for row in email_info:
                    text = row.text
                    html = row.html

            elif generic_count < 3:
                print('Send no smart products email')

                email_id = 5
                str_sql = 'select * from emails where id = 5 limit 1'
                email_info = session_main.execute(str_sql)

                for row in email_info:
                    text = row.text
                    html = row.html

            else:
                print('Send long_session email')
                email_id = 6
                str_sql = 'select * from emails where id = 6 limit 1'
                email_info = session_main.execute(str_sql)

                for row in email_info:
                    text = row.text
                    html = row.html

        email_uuid = str(uuid.uuid4())

        html = html.replace('{confirm_key}', confirm_key)
        html = html.replace('{feedback_key}', email_uuid)
        html = html.replace('{unsub_key}', unsub_key)
        html = html.replace('{email_uuid}', email_uuid)

        str_sql = 'insert into user_feedback (uuid, user_id, date_time) values ("' + str(email_uuid) + '", "' + str(user_id) + '", now())'

        session_main.execute(str_sql)

        msg = MIMEMultipart('alternative')
        msg['From'] = 'TopSavings <adam@TopSavings.com>'
        msg['To'] = email_address

        part1 = MIMEText(text, 'plain')
        msg.attach(part1)

        part2 = MIMEText(html, 'html')
        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)

        msg['Subject'] = 'Welcome to TopSavings'
        server.sendmail("adam@TopSavings.com", email_address, msg.as_string())

        server.quit()

        str_sql = 'insert into emails_sent (emails_id, user_id, email_address, date_time_scheduled, date_time_sent, uuid) values ("' + str(email_id) + '", "' + str(user_id) + '","' + email_address + '", now(), now(),"' + str(email_uuid) + '")'

        session_main.execute(str_sql)
        session_main.commit()
        session_main.close()

    except Exception as e:
        print(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
