import csv
import os

level = raw_input("Please enter oppo level: ")
numFiles = raw_input("Please enter max number of files to combine: ")

class game_state:
  expectedPayoff = 0
  count = 0

  def __init__(self):
	self.expectedPayoff = 0.0;
	self.count = 0;

  def update(self, payoff):
	totalPayoff = self.expectedPayoff * self.count
	self.count += 1
	self.expectedPayoff = (totalPayoff + payoff) / self.count

  def average(self):
  	if (self.count != 0):
  		self.expectedPayoff = self.expectedPayoff / self.count 

  def display(self):
	return(str(self.expectedPayoff) + " " + str(self.count) + ",")

tables = []
w, h = 40, 133
for i in range(4):
	tables.append([[game_state() for i in range(w)] for j in range(h)])

for i in range(1, int(numFiles) + 1):
	qlearningFile = "oppo_" + level + "_c" + str(i) + ".csv"
	exists = os.path.isfile(qlearningFile)
	if not exists:
		print(qlearningFile + " is not found")
	else:
		with open(qlearningFile, 'r') as csvFile:
			stored_table = list(csv.reader(csvFile))
			# update for table type 1
			for i in range(1, 133):
				for j in range(0, 40):
					parsedInput = stored_table[i][j].split(" ")
					tables[0][i-1][j].expectedPayoff += float(parsedInput[0]) * int(parsedInput[1])
					tables[0][i-1][j].count += int(parsedInput[1])
			# update for table type 2
			for i in range(135, 267):
				for j in range(0, 40):
					parsedInput = stored_table[i][j].split(" ")
					tables[1][i-135][j].expectedPayoff += float(parsedInput[0]) * int(parsedInput[1])
					tables[1][i-135][j].count += int(parsedInput[1])
			# update for table type 3
			for i in range(269, 401):
				for j in range(0, 40):
					parsedInput = stored_table[i][j].split(" ")
					tables[2][i-269][j].expectedPayoff += float(parsedInput[0]) * int(parsedInput[1])
					tables[2][i-269][j].count += int(parsedInput[1])
			# update for table type 4
			for i in range(403, 535):
				for j in range(0, 40):
					parsedInput = stored_table[i][j].split(" ")
					tables[3][i-403][j].expectedPayoff += float(parsedInput[0]) * int(parsedInput[1])
					tables[3][i-403][j].count += int(parsedInput[1])

		csvFile.close()

for i in range(4):
	[[state.average() for state in row] for row in tables[i]]

# write to the csv file
download_dir = "oppo_" + level + "_combined.csv" #where you want the file to be downloaded to
csv = open(download_dir, "w") #"w" indicates that you're writing strings to the file

for i in range(4):
	csv.write('table' + str(i) + '\n')
	writer = csv.write('\n'.join([''.join(['{:4}'.format(state.display()) for state in row]) for row in tables[i]]))
	csv.write('\n')
csv.close()
