import calendar
import datetime
import smtplib

from simpledoge import db
from email.mime.text import MIMEText
from flask import current_app


def get_typ(typ, address, window=True):
    """ Gets the latest slices of a specific size. window open toggles
    whether we limit the query to the window size or not. We disable the
    window when compressing smaller time slices because if the crontab
    doesn't run we don't want a gap in the graph. This is caused by a
    portion of data that should already be compressed not yet being
    compressed. """
    # grab the correctly sized slices
    base = db.session.query(typ).filter_by(user=address)
    if window is False:
        return base
    grab = typ.floor_time(datetime.datetime.utcnow()) - typ.window
    return base.filter(typ.time >= grab)


def compress_typ(typ, address, workers):
    for slc in get_typ(typ, address, window=False):
        slice_dt = typ.upper.floor_time(slc.time)
        stamp = calendar.timegm(slice_dt.utctimetuple())
        workers.setdefault(slc.worker, {})
        workers[slc.worker].setdefault(stamp, 0)
        workers[slc.worker][stamp] += slc.value


def send_mail(addresses, message, subject):
    """ Sends a message to a list of recipients """
    try:
        econf = current_app.config['email']
        send_addr = econf['send_address']
        host = smtplib.SMTP(
            host=econf['server'],
            port=econf['port'],
            local_hostname=econf['ehlo'],
            timeout=econf['timeout'])
        host.set_debuglevel(econf['debug'])
        if econf['tls']:
            host.starttls()
        if econf['ehlo']:
            host.ehlo()

        host.login(econf['username'], econf['password'])
        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        msg = MIMEText(message)
        msg['Subject'] = subject
        msg['From'] = 'Simple Doge <simpledogepool@gmail.com>'
        msg['To'] = ', '.join(addresses)
        host.sendmail(send_addr, [addresses], msg.as_string())

    except smtplib.SMTPException:
        current_app.logger.warn('Email unable to send', exc_info=True)
        return False
    else:
        host.quit()

    return True
