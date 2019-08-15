"""
Slave process for a distributed genetic algorithm using Google Sheets API

Created by Nicholas Harris
"""

from __future__ import print_function
import os
import random
import sys
import time
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

#I use my implementation of Markov Network Brains (https://github.com/nicholasharris/Markov-Brains-Python)
#  to test the larger distributed GA template, and for the purpose of demonstration. Any kind of GA can be used
#  so long as the chromosomes of the population can be written to Google Sheet cells
import markov

#A constant to store the sheet ID that you want to work with.
# Check out https://developers.google.com/sheets/api/quickstart/python for info on using Google Sheets API
GENOME_SHEET_ID = 'your_sheet_ID_here'

#A constant to determine the number of chromsomes that this slave process should
#  handle at once. This may be modified to suit your purposes.
NUM_CLAIMS = 100
      
def Eval_Genomes():
    global NUM_CLAIMS

    START_INDEX = int(sys.argv[1]) #starting index on the sheet passed in via the command line (see the READ ME for details).


    #Go through the sheets authentication process in case you haven't already

    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()

    claim_range = ""


    #This slave process will repeat the cycle of waiting for new chromosomes and evaluating them, forever.
    while True: 
        brains = []
        result = []
        nets = []

        endTrainFlag = False

        #Slave process; find genomes in sheet for me to use
        print("Collecting Genomes.")

        doneFlag = False
        numGenomes = 0
        while doneFlag == False:
            #Check that genomes are present in the sheet
            genome_range = 'G1:G50000'
            try:
                result = service.spreadsheets().values().get(
                spreadsheetId=GENOME_SHEET_ID, range=genome_range).execute()
            except:
                print("I encountered an error.")
                time.sleep(30)
                continue
            if result.get('values') is None:
                time.sleep(18)
                #print("empty")
                continue
            else:
                numGenomes = result.get('values')
                numGenomes = len(numGenomes)
                doneFlag = True

        doneFlag = False
        while doneFlag == False:

            numGenomes = 0
            while doneFlag == False:
                #Check that genomes are present in the sheet
                genome_range = 'G1:G50000'
                try:
                    result = service.spreadsheets().values().get(
                        spreadsheetId=GENOME_SHEET_ID, range=genome_range).execute()
                except:   
                    print("I encountered an error.")
                    time.sleep(30)
                    continue
                if result.get('values') is None:
                    time.sleep(18)
                    #print("empty")
                    continue
                else:
                    numGenomes = result.get('values')
                    numGenomes = len(numGenomes)
                    doneFlag = True
            doneFlag = False
            #Read Flag range to find available genomes
            flag_range = "D" + str(START_INDEX) + ":D" + str(START_INDEX + NUM_CLAIMS - 1)
            values = []
            try:
                result = service.spreadsheets().values().get(
                    spreadsheetId=GENOME_SHEET_ID, range=flag_range).execute()
            except:
                print("I encountered an error.")
                time.sleep(30)
                continue
            numClaimed = result.get('values') if result.get('values')is not None else 0
            #if result.get('values') is not None:
            #    numClaimed = len(numClaimed)
            if result.get('values') is None:  #No claimed genomes
                #Claim number of genomes immediately
                claims = []
                for x in range(NUM_CLAIMS):
                    claims.append( ["CLAIMED"] )
                claim_range = "D" + str(START_INDEX) + ":D" + str(START_INDEX + NUM_CLAIMS - 1)

                body = {
                    'values': claims
                    }

                try:
                    result = service.spreadsheets().values().update(spreadsheetId=GENOME_SHEET_ID,range=claim_range,valueInputOption='RAW', body=body).execute()
                except:
                    print("I encountered an error.")
                    time.sleep(30)
                    continue
            
    
                #Read the genomes we have claimed from the sheet
                
                genome_range = "G" + str(START_INDEX) + ":G" + str(START_INDEX + NUM_CLAIMS - 1)
                try:
                    result = service.spreadsheets().values().get(
                        spreadsheetId=GENOME_SHEET_ID, range=genome_range).execute()
                except:
                    print("I encountered an error.")
                    time.sleep(30)
                    continue
                if result.get('values') is None:
                    range_ = "D" + str(START_INDEX) + ":D" + str(START_INDEX + NUM_CLAIMS - 1)  

                    clear_values_request_body = {
                       
                    }

                    clearFlag = False
                    while clearFlag == False:
                        try:
                            request = service.spreadsheets().values().clear(spreadsheetId=GENOME_SHEET_ID, range=range_, body=clear_values_request_body)
                            response = request.execute()
                            clearFlag = True
    
                        except:
                            print("I encountered an error.")
                            time.sleep(30)
                            clearFlag = True
                            continue
                    continue
                brains = []  #I collect the genomes and put them into the markov brain object according to its structure.
                             # The way you construct phenotype from genotype is dependant on the specifics of your GA.
                for x in range(NUM_CLAIMS):
                    sequence = []
                    genome = result.get('values')[x][0]
                    value = ""
                    for y in range(len(genome)):
                        
                        if genome[y] != ',':
                            value = value + genome[y]
                        else:
                            if value != "":
                                sequence.append(int(value))
                            value = ""

                    current_genome = markov.Genome(len(sequence))
                    for y in range(len(sequence)):
                        current_genome.sequence[y] = sequence[y]

                    brain = markov.MarkovBrain(16, current_genome.length, 1, 0, current_genome)
                    brains.append(brain)

                                      
                
                doneFlag = True
            else:   # all genomes are claimed, wait patiently
                time.sleep(18)
                
            
                
        doneFlag = False 

        #Now that you have collected a bunch of chromosome and constructed the phenotype,
        #  evaluate the brains according to whatever problem domain you are working with.
        #  This can range from very simple to very complex and is entirely up to you.
        #  Here I return an arbitrary fitness for the purpose of demonstration.
        #      I also include room in the sheet for a "validation fitness", or more generally
        #       you may just think of it as a secondary notion of fitness if you have need for it.
        for brain in brains:
            brain.fitness = 100.0 #arbitrary
            brain.validation_fitness = 100.0 #arbitrary

        #write fitness values to sheet
        fitness_range = claim_range.replace('D', 'F')
        val_range = claim_range.replace('D', 'E')

        values = []
        for c in range(len(brains)):
            myList = []
            myStr = str(brains[c].fitness)
            myList.append(myStr)
            values.append(myList)

        body = {
                'values': values
            }

        
        doneFlag = False
        while doneFlag == False:
            try:
                result = service.spreadsheets().values().update(spreadsheetId=GENOME_SHEET_ID,range=fitness_range,valueInputOption='RAW', body=body).execute()
                doneFlag = True
            except:
                print("I encountered an error.")
                time.sleep(30)
                doneFlag = False

        #If you have no need for 2 notions of fitness you may discard this second round of writing
        values = []
        for c in range(len(brains)):
            myList = []
            myStr = str(brains[c].validation_fitness)
            myList.append(myStr)
            values.append(myList)

        body = {
                'values': values
            }

        doneFlag = False
        while doneFlag == False:
            try:
                result = service.spreadsheets().values().update(spreadsheetId=GENOME_SHEET_ID,range=val_range,valueInputOption='RAW', body=body).execute()
                doneFlag = True
            except:
                print("I encountered an error.")
                time.sleep(30)
                doneFlag = False
        
        
       




##### "Main" content ######

# Go through the Google Sheets API authentication if you haven't already.

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server()
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('sheets', 'v4', credentials=creds)

print("setup finished; entering Eval_Genomes loop")   #Slave process has started and will enter its running loop indefinitely.
Eval_Genomes()

