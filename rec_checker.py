#!/Users/cjurich/opt/miniconda3/bin/python3
import urllib.request
from bs4 import BeautifulSoup
import re
import datetime

###################################################################################
############################## CONSTANTS ##########################################
city_weights_URL = "https://shopcrec.unl.edu/wbwsc/webtrac.wsc/search.html?display=calendar&module=AR&keyword=strength&location=CREC&_ga=2.22302008.2083201124.1597015035-1723204169.1591553160"
###################################################################################
####################### HELPER FUNCTIONS ##########################################
def get_date_from_href(href):
    """Helper method that gets date from a hypertext link. Assumes format of MM/DD/YYYY. Raises error if number of matches != 1"""
    matches = re.findall('[0-9]{2}/[0-9]{2}/[0-9]{4}',href)
    if len(matches) != 1:
        raise Exception("number of matches is incorrect. Should be 1 but is {}".format(len(matches)))
    return matches[0]
def get_time_from_text(text):
    """Helper method that gets the time from a html text. Assumes format of HH:MM [am|pm]- HH:MM [am|pm]"""
    matches = re.findall('[0-9 ][0-9]\:[0-9]{2} [ap]m',text)
    if len(matches) != 2:
        raise Exception("number of matches is incorrect. Should be 2 but is {}".format(len(matches)))
    start = float(matches[0].rsplit(' ',1)[0].replace(':','.')) +( 12. if matches[0].rsplit(' ',1)[1] == "pm" else 0.)
    end = float(matches[1].rsplit(' ',1)[0].replace(':','.')) + (12. if matches[1].rsplit(' ',1)[1] == "pm" else 0.)
    if start == 24: start = 12
    return start,end

def get_spots_fromt_text(text):
    """Helper method that gets the number of total and available spots from the html text. Assumes a format of "XX of XX Available"""
    matches = re.findall("[0-9]{1,}",text.rsplit('m',1)[-1])
    if len(matches) != 2:
        raise Exception("number of matches is incorrect. Should be 2 but is {}".format(len(matches)))
    available = int(matches[0])
    total = int(matches[1])
    return available,total

###################################################################################
################################ CLASSES ##########################################

class TermColor:
    """Enum class holding ASCII terminal colors"""
    black= "\u001b[30m"
    red = "\u001b[31m"
    green =  "\u001b[32m"
    yellow = "\u001b[33m"
    blue =  "\u001b[34m"
    magenta = "\u001b[35m"
    cyan = "\u001b[36m"
    white = "\u001b[37m"
    reset = "\u001b[0m"

class LiftTime:
    """Class representing a lift time"""
    def __init__(self,**kwargs):
        self.start_time=float()
        self.end_time=float()
        self.spots_remaining = int()
        self.date=str()
        self.fill_level=str()

        for variable, value in kwargs.items():
            setattr(self,variable,value)

    def __str__(self):
        """String converion for a lift time. Color changes depending on number of spots left."""
        if self.fill_level == "low":
            color = TermColor.green
        elif self.fill_level == "medium":
            color = TermColor.yellow
        elif self.fill_level == "high":
            color = TermColor.red
        return "{COLOR_START}{CURR} spots{RESET}".format(
                COLOR_START=color,CURR=(" " if self.spots_remaining < 10 else "" )+ str(self.spots_remaining),RESET=TermColor.reset
                )

class LiftCalendar:
    """Class that holds the lift times and delays them"""
    def __init__(self,**kwargs):
        self.days = list()
        self.times = tuple((9,10,11,12,13,14,15,16,17,18,19,20,21))
        self.lift_holder = dict()

        for variable, value in kwargs.items():
            setattr(self,variable,value)

    def display(self):
        """Driver method that displays lift availablity information"""
        output = str()
        preamble ="UNL City campus weight room avaiability\n\n"
        header = " | ".join(["   time  "] + self.days)
        divider = '-'*len(header)
        body = []

        for time in self.times:
            line = " {TIME}:00 {MER}m".format(
                    TIME=str(time if time <= 12 else time -12),
                    MER='a' if time < 12 else 'p'
                    )
            line += " "*(10-len(line))
            for day in self.days:
                if (day,time) not in self.lift_holder:

                    if day == self.days[0]: # and time <= datetime.datetime.now().hour:
                        line += "|" + "   passed   "
                    else:
                        line += "|" + " not opened "
                else:
                    new_entry = str(self.lift_holder[(day,time)])
                    excess = 22 - len(new_entry)
                    line += "|" + ' '*int(excess*0.5) +new_entry +' '*int(excess*0.5)
            body.append(divider)
            body.append(line)

        end = "\n\n   Availablity as of {TIME}\n        Subject to change".format(
            TIME=datetime.datetime.now().date())

        print("\n".join( [preamble,
            header] + body +[end] ))

###################################################################################
######################### FREE FUNCTIONS ##########################################


def build_lift_times():
    """Method that pulls lift times from the UNL rec center website. HTML is parsed and then a list of LiftTime's is returned"""
    try:
        contents = urllib.request.urlopen(city_weights_URL).read().decode('utf-8')
        parsed_html = BeautifulSoup(contents,"html.parser")
    except Exception as Error:
        print("{RED}Unable to make proper connection.\nCheck that you are connected to the internet AND have approrpriate modules installed.\nTerminating due to error:{RESET} {ERR}".format(
            ERR=Error,RESET=TermColor.reset,RED=TermColor.red
            ))
        exit()

    lift_times = []

    for section in parsed_html.find_all('a'):
        if section.get_text().find("Available") != -1 and section.get_text().find("of ") != -1:
            link = section['href']

            if len(link) > 8:
                # extracting contents from the html
                text = section.get_text()
                start, end = get_time_from_text(text)
                date = get_date_from_href(section['href'])
                available, total = get_spots_fromt_text(section.get_text())
                # convert to LiftTime object and add to the lift_times lsit
                lift_times.append(LiftTime(**{
                    "start_time" : start,
                    "end_time" : end,
                    "spots_remaining" : available,
                    "date" : date,
                    "fill_level" : "low" if available > 30 else ("medium" if available > 15 else "high")

                    }
                    ))

    return lift_times

def build_lift_calendar(lift_times):
    """Method that takes a list of lif times and turns them into a LiftCalendar object"""
    days = set()
    lift_dict = dict()

    for lift in lift_times:

        days.add(lift.date)
        lift_dict[(lift.date,lift.start_time)] = lift

    return LiftCalendar(**{
            "days" : sorted(list(days)),
            "lift_holder" : lift_dict
        })

def main():
    lift_times = build_lift_times()
    lift_calendar = build_lift_calendar(lift_times)
    lift_calendar.display()

###################################################################################


if __name__ == "__main__":
    main()

