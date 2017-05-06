from oauth2client.service_account import ServiceAccountCredentials
import concurrent.futures
import getpass
import gspread
import json
import praw
import re

# Variables, change these when the government etc changes
sheetName = '15th Govt Voting Record'  # Identify what 'tab' the votes are on
sheetKey = '1Wl7gnsi2czK-MrCyVkXTidR3qJOMXyOkfApPsocveJs'  # unique identifier
# for the spreadsheet
accessKey = 'ServiceKey.json'  # location of the file with logins
totalMPs = 102  # For turnout
lastCellOnSheet = 'BZ'

authorisedProxies = []


###############################################################################
###################################FUNCTIONS###################################
###############################################################################
def count(thread):
    global r
    global sheet
    global bottomRow
    global authorisedProxies

    aye = 0
    no = 0
    abstain = 0
    dnv = 0
    # Get latest vote column
    vote_cells = sheet.range('F2:' + lastCellOnSheet + '2')
    for cell in vote_cells:
        if cell.value == '':
            col = cell.col
            break
    # auto-DNV
    vote_list = sheet.range(sheet.get_addr_int(3, col) + ':' +
                            sheet.get_addr_int(bottomRow, col))
    for cell in vote_list:
        if not cell.value.lower() == 'N/A'.lower():
            cell.value = 'DNV'
            dnv += 1
    sheet.update_cells(vote_list)

    sub = r.get_submission(thread)

    # do the bill title
    title = str(sub.title)
    billName = str(re.search('^(\S+)', title).group())
    sheet.update_cell(2, col, '=HYPERLINK("' + thread + '", "' + billName + '")')

    # count votes
    already_done_id = []
    already_done_name = []
    dupes = []
    # Get all the comments
    sub.replace_more_comments(limit=None, threshold=0)
    comments = praw.helpers.flatten_tree(sub.comments)

    # Get all the voters
    authors_cells = sheet.range('C3:' + sheet.get_addr_int(bottomRow, 3))
    authors = []
    for author in authors_cells:
        authors.append(str(author.value).lower())
    # iterate through the votes
    for comment in comments:
        print(str(comment.author) + ': ' + comment.body)
        if comment.author in already_done_name:
            print('ALERT: POSSIBLE DOUBLE VOTING ' + str(comment.author))
            dupes.append(comment.author)
        if comment.id not in already_done_id and (
                str(comment.author).lower() not in 'automoderator' or str(comment.author).lower() not in 'None'):
            messageContent = ''
            try:
                if 'proxy' in str(comment.body).lower():
                    if str(comment.author).lower() in authorisedProxies:
                        author = re.search('(?<=\/u\/)\S+', str(comment.body).lower()).group(0).lower()
                        row = 3 + authors.index(author)
                        if 'aye' in str(comment.body).lower():
                            aye += 1
                            dnv -= 1
                            messageContent = 'Aye'
                        elif 'nay' in str(comment.body).lower() or 'no' in str(comment.body).lower():
                            no += 1
                            dnv -= 1
                            messageContent = 'No'
                        elif 'abstain' in str(comment.body).lower():
                            abstain += 1
                            dnv -= 1
                            messageContent = 'Abs'
                        if messageContent != '' and sheet.acell(sheet.get_addr_int(row,
                                                                                   col)).value != 'N/A':
                            sheet.update_cell(row, col, messageContent)
                elif str(comment.author).lower() in authors:
                    already_done_id.append(comment.id)
                    already_done_name.append(comment.author)
                    row = 3 + authors.index(str(comment.author).lower())
                    if 'aye' in str(comment.body).lower():
                        aye += 1
                        dnv -= 1
                        messageContent = 'Aye'
                    elif 'no' in str(comment.body).lower():
                        no += 1
                        dnv -= 1
                        messageContent = 'No'
                    elif 'abstain' in str(comment.body).lower():
                        abstain += 1
                        dnv -= 1
                        messageContent = 'Abs'
                    if messageContent != '' and sheet.acell(sheet.get_addr_int(row,
                                                                               col)).value != 'N/A':
                        sheet.update_cell(row, col, messageContent)
                    else:
                        dupes.append(comment.author)
                else:
                    print('well thats not in the list...')
            except gspread.exceptions.CellNotFound:
                print('Automoderator Comment')
    print('Dupes are:' + str(dupes))
    print('Done')
    print('Aye: ' + str(aye))
    print('No: ' + str(no))
    print('Abstain: ' + str(abstain))
    print('No Vote: ' + str(dnv))
    print('Turnout: ' + str(float((totalMPs - dnv) / totalMPs)))
    print('===========================')


#   Initilises all the credentials, and GoogleSheet stuff
scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('ServiceKey.json', scope)
r = praw.Reddit('MHOC-plebian house, vote counter v1')
gc = gspread.authorize(credentials)
sh = gc.open_by_key(sheetKey)
sheet = sh.worksheet(sheetName)

#   User Input for Reddit/ Reddit information
user = str(input('Reddit Username: '))
password = str(input('Reddit Password: '))
r.login(user, password)
print('Post Voting Thread Link')
thread = str(input())
bottomRow = int(sheet.find('Speaker').row) - 1  # For use in script to calculate once

count(thread)