# Dependencies
import pandas as pd

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
from matplotlib import gridspec

import os

import numpy

import glob



# Set location of input files
# Targeting and IS Reports use wildcards so we can glob and merge multiples with different dates
tr_path = 'Resources/Targeting_Reports/*.csv'
is_path = 'Resources/Searchterm_IS_Reports/*.csv'
hist_path = 'Resources/bid_history.csv'

# Read History as DataFrame
hist_df = pd.read_csv(hist_path, parse_dates=['Date'])

hist_df = hist_df.replace('#VALUE!',numpy.nan)

# Initialise DF Variables
tr_df = None
is_df = None

# Read all targeting reports in folder and merge to DataFrame
for path in glob.glob(tr_path):
	if tr_df is None:
		tr_df = pd.read_csv(path, parse_dates=['Date'])
	else:
		df = pd.read_csv(path, parse_dates=['Date'])
		tr_df = pd.concat([tr_df, df])
tr_df = tr_df.drop_duplicates(subset=['Date', 'Targeting', 'Ad Group Name']).reset_index()

# Read all Impression Share reports in folder and merge to DataFrame
for path in glob.glob(is_path):
	if is_df is None:
		is_df = pd.read_csv(path, parse_dates=['Date'])
	else:
		df = pd.read_csv(path, parse_dates=['Date'])
		is_df = pd.concat([is_df, df])
is_df = is_df.drop_duplicates(subset=['Date', 'Customer Search Term', 'Ad Group Name']).reset_index()
is_df = is_df.loc[is_df['Match Type'] == 'EXACT'][['Date', 'Customer Search Term', 'Ad Group Name','Search Term Impression Rank', 'Search Term Impression Share']]


# Merge IS into TR Dataframe on each date for exact targets
tr_df = pd.merge(tr_df,is_df, left_on=['Date', 'Targeting', 'Ad Group Name'], right_on=['Date', 'Customer Search Term', 'Ad Group Name'],how='outer')

print(tr_df.head())



# Create array of dates
dates = pd.to_datetime(tr_df.Date.unique())


# Create array of ad groups to select
adgroups = hist_df.loc[hist_df.Date.isin(dates)]['Ad Group'].unique()

# Set up global config for matplotlib
plt.rcParams["figure.figsize"] = [10, 6]
plt.rcParams["figure.autolayout"] = True


# Iterate through every ad group that has changes in the time frame of the report
for ag in adgroups:

	print(f'Starting Ad Group: {ag}')
	
	# For Testing DELETE WHEN DONE
	# ag = 'Active Detergent - SP - KW - Main - KW Exact - Set 1'

	path = f"Images/{dates.min().strftime('%Y.%m.%d')}_{dates.max().strftime('%Y.%m.%d')}/{ag}/"

	# Check whether the specified path exists or not
	isExist = os.path.exists(path)

	if not isExist:
  
  		# Create a new directory because it does not exist 
 		os.makedirs(path)


	#Select all the unique keywords that have bid history in this ad group
	keywords = hist_df.loc[(hist_df['Ad Group'] == ag) & (hist_df.Date.isin(dates))].Keyword.unique()

	#Find min and max of bids
	bid_min = hist_df.loc[(hist_df['Ad Group'] == ag)][['From Bid', 'To Bid']].astype('float').min().min()
	bid_max = hist_df.loc[(hist_df['Ad Group'] == ag)][['From Bid', 'To Bid']].astype('float').max().max()
	bid_min = min(bid_min,tr_df.loc[(tr_df['Ad Group Name'] == ag)]['Cost Per Click (CPC)'].astype('string').str.replace('$','', regex=False).astype('float').min())
	bid_max = max(bid_max,tr_df.loc[(tr_df['Ad Group Name'] == ag)]['Cost Per Click (CPC)'].astype('string').str.replace('$','', regex=False).astype('float').max())

	# Iterate through each keyword to generate the graph
	for kw in keywords:

		# For Testing DELETE WHEN DONE
		# kw = 'sport laundry detergent'

		print(f'Starting keyword: {kw}')

		# Establish the axes and the figure to plot
		fig,(ax1,ax4,ax6) = plt.subplots(nrows=3, sharex=True, gridspec_kw={'height_ratios': [3, 1, 2], 'hspace': 0})
		ax2 = ax1.twinx()
		ax3 = ax6.twinx()

		# Find dates of bid changes
		changes = hist_df.loc[(hist_df['Ad Group'] == ag) & (hist_df['Keyword'] == kw) & (hist_df.Date.isin(dates))].Date

		# For First AXIS set color and labels
		ax1.spines.right.set_color('b')
		ax1.tick_params(axis='y', colors='b')
		ax1.set(ylabel='Impressions')


		# For Second AXIS set color and labels
		ax2.spines.right.set_color('r')
		ax2.set_ylim([bid_min, bid_max])
		ax2.yaxis.set_major_formatter('${x:1.2f}')

		#Set up Impression Share label
		ax6.tick_params(axis='y', colors='b')
		ax6.set(ylabel='IS Rank')

		# Set up ROAS Axis
		ax3.tick_params(axis='y', colors='g')
		ax3.set(ylabel='RoAS')

		#Format Y of CTR/CR Graph
		ax4.yaxis.set_major_formatter(mtick.PercentFormatter())
		ax4.set(ylabel='CTR')
		ax4.tick_params(axis='y', colors='b')

		ax5 = ax4.twinx()
		ax5.yaxis.set_major_formatter(mtick.PercentFormatter())
		ax5.set(ylabel='CR')
		ax5.tick_params(axis='y', colors='r')



		# Set Title of the chart to this keyword
		ax1.set_title(kw)

		# Merge History and Targeting Dataframes so we can show the bids on the same axis as the performance
		this_df = pd.merge(tr_df.loc[(tr_df['Ad Group Name'] == ag) & (tr_df.Targeting == kw)], hist_df.loc[(hist_df['Ad Group'] == ag) & (hist_df.Keyword == kw) & (hist_df.Date.isin(dates))], how='outer', on='Date')
		this_df.set_index('Date')
		# Backwards fill the starting bids for every change to get the initial values for each date
		this_df['From Bid'] = this_df['From Bid'].bfill()

		# Forward fill the Changed bids to get the new values for each date
		# This ignores the values before the first change so we fill those with the back
		# filled values from above
		this_df['Bid'] = this_df['To Bid'].ffill().fillna(this_df['From Bid'])


		#Convert Necessary columns of DataFrame to Numeric so we can plot them
		try:
			this_df["Click-Thru Rate (CTR)"] = this_df["Click-Thru Rate (CTR)"].astype('string').str.rstrip('%').astype('float')
			this_df["7 Day Conversion Rate"] = this_df["7 Day Conversion Rate"].astype('string').str.rstrip('%').astype('float')
			this_df["Cost Per Click (CPC)"] = this_df["Cost Per Click (CPC)"].astype('string').str.replace('$','', regex=False).astype('float')
		except:
			pass

		# Set up moving averages for some of the metrics
		this_df['CTR Moving'] = this_df["Click-Thru Rate (CTR)"].rolling(7).mean()
		this_df['CR Moving'] = this_df["7 Day Conversion Rate"].rolling(7).mean()
		this_df['ROAS Moving'] = this_df["Total Return on Advertising Spend (RoAS)"].rolling(7).mean()


		# this_df.iloc[:,2:] = this_df.iloc[:,2:].apply(pd.to_numeric, errors='coerce')

		# Plot Area of Impressions
		this_df.plot(x='Date', y=["Impressions"], ax=ax1, legend=False, alpha=0.65)
		numeric_date = this_df.Date.values
		ax1.fill_between(numeric_date, this_df.Impressions, interpolate=True, alpha=0.65)


		# Plot values on the respective Axes
		this_df.plot(x='Date', y='ROAS Moving', ax=ax3, color='g', legend=False)

		# Plot CTR, CR
		this_df.plot(x='Date', y=['CTR Moving'], ax=ax4, legend=False)
		this_df.plot(x='Date', y=["CR Moving"], color='red', ax=ax5, legend=False)

		# Plot IS Ranks
		this_df.plot(x='Date', y='Search Term Impression Rank', ax=ax6, legend=True)



		try:
			this_df.plot(x='Date', y="Cost Per Click (CPC)", ax=ax2, color='purple', legend=False)
		except:
			pass

		#Check if there were bid changes so we can avoid type error
		if changes.size > 0:

			# Cast Bid as numeric
			this_df.Bid = this_df.Bid.astype('float')
			#Plot Bids
			this_df.plot(x='Date', y="Bid", ax=ax2, color='r', legend=False)

			# Add lines for Bid Changes
			for line in changes:
				ax1.axvline(x=line, linestyle='dashed', color='r')
				ax4.axvline(x=line, linestyle='dashed', color='r')
				ax6.axvline(x=line, linestyle='dashed', color='r')

		# Rotate and align the tick labels so they look better.
		fig.autofmt_xdate()

		# Use a more precise date string for the x axis locations in the toolbar.
		ax1.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
		ax4.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')
		ax6.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')

		# Set up Legends
		ax1.plot(numpy.nan, '-r', label = 'Bid')
		ax1.plot(numpy.nan, 'purple', label = 'CPC')
		ax4.plot(numpy.nan, '-r', label = 'CR Moving')
		ax6.plot(numpy.nan, 'green', label = 'ROAS')


		ax1.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))
		ax4.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))
		ax6.legend(loc='center left', bbox_to_anchor=(1.2, 0.5))


 		# Save an image of this graph to the folder for this ad group
		plt.tight_layout()
		plt.savefig(f"{path}/{kw}.png")

		# Close the current chart before ending the loop to reduce memory usage
		plt.close()


		

