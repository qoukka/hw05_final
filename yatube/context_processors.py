import datetime as dt


def year(request):
    now = dt.datetime.today()
    return {
        'year': now.year
    }