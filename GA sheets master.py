"""
Master process for a distributed genetic algorithm using Google Sheets API

Created by Nicholas Harris
"""

from __future__ import print_function
import os
import random
import sys
import time
import datetime
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


#Ths number is arbitrary; set whatever criteria you wish
NUM_GENS = 5000


#This function sends out the chromosomes to your designated Google sheet,
#   waits for the slave processes to finish evaluating the chromsomes (assign a fitness),
#   then performs the GA operations to create a new generation so the cycle can repeat
def Eval_Genomes(myPopulation, maxGens):

    gen = 0

    result = []

    # Do the authentication here as well just in case

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



    #Here is the main GA loop, that repeats for a set number of generations
    while gen < maxGens:
        #Master Process, write all genomes to sheet
        print("Clearing sheet.")

        start = time.time()
        #Clear Genomes Sheet
        # Call the Sheets API
        sheet = service.spreadsheets()

        range_ = 'A1:G50000'  # clears the sheet up to a very high value of 50,000 columns. You may reduce this if you wish.

        clear_values_request_body = {
           
        }

        # You will find many of these try/except statements; they assure the entire process doesn't grind to a halt due to a temporary lost
        # connection, but allows recovery. You may be able to improve efficiency in waiting times through experimentation.
        try:
            request = service.spreadsheets().values().clear(spreadsheetId=GENOME_SHEET_ID, range=range_, body=clear_values_request_body)
            response = request.execute()
        except:
            print("I encountered an error.")
            time.sleep(30)
            continue

        end = time.time()
        print("Sheet cleared. Time elapsed: " + str(end - start) )

        

        print("Collecting Genomes.")

        start = time.time()
        # Write all genomes to the Google sheet. I obtain the genomes as defined in my implemenation of Markov Network Brains.
        #   Any chromosome will do, just convert it into a string and separate values with a comma, as I do below.
        range_ = 'G1:G50000'
        values = []
        for x in range(len(myPopulation.brains)):
            myList = []
            myStr = ""
            
            for y in range(len(myPopulation.brains[x].genome.sequence)):
                myStr = myStr + str(myPopulation.brains[x].genome.sequence[y]) + ","

            myList.append(myStr)
            values.append(myList)
        end = time.time()
        print("Time elapsed: " + str(end - start))  #I calculate the time for different phases of the API communication (writing genomes is the longest)

        print("Writing to sheet")

        start = time.time()

        body = {
            'values': values
        }

        try:
            result = service.spreadsheets().values().update(spreadsheetId=GENOME_SHEET_ID,range=range_,valueInputOption='RAW', body=body).execute()
        except:
            print("I encountered an error.")
            time.sleep(30)
            continue
        print('{0} cells updated.'.format(result.get('updatedCells')))
        end = time.time()
        print("Time elapsed: " + str(end - start) )  # I found transfering the data on a very large population could take almost a minute,
                                                     #    a little long but on many problem domains this time will be dwarfed by the time needed to evalute all the chromosomes
        
        doneFlag = False
        fitnesses = []
        val_fitnesses = []
        while doneFlag == False:
            #wait until all genomes have been evaluated, then calculate the next generation
            fitness_range = 'E1:E50000'
            result = []
            try:
                result = service.spreadsheets().values().get(
                    spreadsheetId=GENOME_SHEET_ID, range=fitness_range).execute()
            except:
                print("I encountered an error.")
                time.sleep(30)
                continue
            if result.get('values') is None:
                time.sleep(10)
                #print("empty")
                continue
            
            numRows = result.get('values') if result.get('values')is not None else 0

            #If all fitnesses have been assigned, exit loop to calculate next generation
            fullFlag = True

            #we wait until we've received enough fitnesses to match the size of our population
            if len(numRows) < len(myPopulation.brains):  
                fullFlag = False
            for x in range(len(numRows)):
                if (numRows[x] is None):
                    fullFlag = False
                    break
                elif (len(numRows[x]) == 0):
                    fullFlag = False
                    break
                elif any(char.isdigit() for char in numRows[x][0]) == False:
                    fullFlag = False
                    break
            if (fullFlag == True):  
                fitness_range = 'F1:F50000'
                try:
                    result = service.spreadsheets().values().get(
                    spreadsheetId=GENOME_SHEET_ID, range=fitness_range).execute()
                except:
                    print("I encountered an error.")
                    time.sleep(30)
                    continue
                fitnesses = result.get('values')
                val_range = 'E1:E50000'
                try:
                    result = service.spreadsheets().values().get(
                    spreadsheetId=GENOME_SHEET_ID, range=val_range).execute()
                except:
                    print("I encountered an error.")
                    time.sleep(30)
                    continue
                val_fitnesses = result.get('values')

                doneFlag = True    
            else:
                #print(len(numRows))
                time.sleep(10)
        
        # After all fitnesses were recorded to the sheet by slave processes, 
        # assign all reported fitnesses to population of brains
        for x in range(len(myPopulation.brains)):
            myPopulation.brains[x].fitness = float(fitnesses[x][0])
            myPopulation.brains[x].validation_fitness = float(val_fitnesses[x][0])
        
        
        gen = gen + 1

        #Clear the sheet for use in the next generation of the GA
        print("Clearing sheet.")

        start = time.time()
        #Clear Genomes Sheet
        # Call the Sheets API
        sheet = service.spreadsheets()

        range_ = 'G1:G50000'  

        clear_values_request_body = {
            
        }

        request = service.spreadsheets().values().clear(spreadsheetId=GENOME_SHEET_ID, range=range_, body=clear_values_request_body)


        doneFlag = False
        while doneFlag == False:
            try:
                response = request.execute()
                doneFlag = True
            except:
                print("I encountered an error.")
                doneFlag = False
                time.sleep(30)
            

        end = time.time()
        print("Sheet cleared. Time elapsed: " + str(end - start) )


        # Now perform the traditional Genetic Algorithm functions (crossover, mutation, selection) to create the next generation, and repeat.
        # All this is implemented in "markov.py", my python implmentation of Markov Network Brains.
        # Your own function(s) may go here to replace this one.
        myPopulation.eval_genomes()

        

########### "Main" content ##########################################################
random.seed()


# Create the population for the Genetic Algorithm
# See the repository for info on my implementation of Markov Network Brains if you're curious about the syntax or population parameters
# Any implemenation of the genetic algorithm will work fine so long as the chromosomes can be written to the sheet.
#   (Most "normal" chromosomes should be no issue).
myPopulation = markov.MarkovPopulation(500, 64, 5000, 1, 30, 70, 0.001, 0.001, 0.001, 0.001, 0.001, 0.001, 0, True, True)

# Make sure to visit https://developers.google.com/sheets/api/quickstart/python
#    and complete all first-time authentication so that you can use the API code that follows

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


# Run the gentic algorithm for an arbitrary number of generations, or set your own stopping point based on your own criteria
print("Running Eval Genomes Loop")
Eval_Genomes(myPopulation, NUM_GENS)


