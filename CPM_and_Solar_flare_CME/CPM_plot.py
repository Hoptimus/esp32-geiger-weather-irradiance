import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob

# List all the matching files
files = glob.glob("Data/*.csv")

dfs = []
for f in files:
    try:
        df = pd.read_csv(f, on_bad_lines='skip')
        df.columns = df.columns.str.strip()
        df['Radiation_CPM'] = pd.to_numeric(df.get('Radiation_CPM'), errors='coerce')
        df['Radiation_uSv_h'] = pd.to_numeric(df.get('Radiation_uSv_h'), errors='coerce')
        df['Source'] = f
        dfs.append(df)
    except Exception as e:
        print(f"Error reading {f}: {e}")

if dfs:
    data = pd.concat(dfs, ignore_index=True)
    
    if 'Date' in data.columns and 'Time' in data.columns:
        data['Datetime'] = pd.to_datetime(data['Date'] + ' ' + data['Time'], errors='coerce')
        # Drop missing data
        data = data.dropna(subset=['Datetime', 'Radiation_CPM'])
        # Sort and reset the index to guarantee a perfect 0, 1, 2... sequence
        data = data.sort_values('Datetime').reset_index(drop=True)
        
    # # Export to Excel
    # export_data = data.drop(columns=['Datetime'], errors='ignore')
    # excel_filename = 'Combined_Radiation_Data.xlsx'
    # export_data.to_excel(excel_filename, index=False)
    # print(f"All data combined and saved to {excel_filename}")

    # Plotting
    plt.figure(figsize=(12, 6))
    
    # PLOT TRICK: Plot against a simple integer sequence, not the Datetime column
    x_index = np.arange(len(data))
    plt.plot(x_index, data['Radiation_CPM'], label='Radiation CPM', color='purple', alpha=0.7, linewidth=1)
    
    # Calculate exactly 10 evenly spaced positions for the x-axis labels
    num_ticks = 10
    tick_positions = np.linspace(0, len(data) - 1, num_ticks, dtype=int)
    
    # Grab the actual Datetime strings for those 10 specific positions
    tick_labels = data['Datetime'].iloc[tick_positions].dt.strftime('%Y-%m-%d %H:%M')
    
    # Apply the custom text labels to the integer grid
    plt.xticks(tick_positions, tick_labels, rotation=45)
    
    plt.xlabel('Date and Time')
    plt.ylabel('Radiation (Counts Per Minute)')
    plt.title('Radiation CPM over Time (Missing Time Skipped)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('radiation_plot.png')
    print("Plot saved as radiation_plot.png")
else:
    print("No data found.")