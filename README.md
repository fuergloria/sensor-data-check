Welcome to my Sensor Data Visualization Project!

The idea for my project came from a friend of mine, who has purchased an air quality sensor, which can generate data for the following parameters:

-Humidity (%)
-Temperature (°C)
-CO2 concentration (ppm)
-Total volatile organic compunds (ppb)
-Light intensity (lux)
-UV index

He already implemented some backend, which generates the data every minute and then saves it in a csv-file, which left him with a lot of relatively raw data. So my idea was to display the data in a more appealing way. The used charts and tables allow for better visibility and easier analyzing of the data. Hence I implemented a web application, which uses python, flask, jinja, html, css, javascript, bootstrap, chart.js. I programmed the application in the codespace.

So first I simply read all the data and put in a table for the first representation. This worked for small data sizes, but since there's going to be a lot of data, when the sensor keeps generating new entries, I didn't want to read all the data everytime the table would be generated. So I didn't pursue this path further. When a table or chart is generated, the user has to specify the time range first, so the app didn't have to handle too much data at once.

Now to the different files in my project:

HTML Templates:

layout.html:
    serves as the base template and contains the navigation bar of the website.
    It links the bootstrap and my own stylesheet and also links the bootstrap script for all my html files.
    Defines two jinja blocks
    -title block
    -main block,

index.html:
    this is the landing page, which is rendered by following the route("/")
    Provides two main pathways:
    -If you only want to browse the data and get an visual overview you can do so by following the link with
      id="btn-chart", which then follows the route("/chart")
    -If you want a table with all the data entry points for a specific time frame, you will be able to specify,
       which   parameters and time frame is relevant to you, and then generate a table. Therefore you have a form with method="POST" and action="/table". This form includes a checkbox for the different parameters and then you have a select dropdown menu with the following predefined timeframes:
        -last hour
        -last 24 hours
        -last week
        -last month
    the last select option is:
      -custom range, which activates date input fields via JavaScript. So by selecting custom range, you'll be able to input the respective start and end date. For showing the hidden fields, I've used EventListener, which is triggered if there's a change in the select menu. if 'custom' is chosen the display property is set to 'block', if not to 'none'.

  chart.html:
    this Site is accessible via routes:
    -/chart
    -/chart/<period>
    -/chart/<period>/<date>
    Default display: humidity data for current day

    Interface elements:
    -Parameter selection form, which allows you to select the parameter, which should be displayed on the chart below.
    -Period selection buttons, meaning the displayed unit of time, hence if the diagram shows a day, a week, a month or a
       year. i've used a jinja for-loop for displaying the buttons, in order to adjust the corresponding links and also to change the classes depending if the period is selected( if yes its a btn-primary, if not btn-secondary). the corresponding links consist of the main route ("/chart") and then the period of the respective button and then the date, which is shown at the time. this information is transmitted in the rendering of the page, but more on that later.
    -Navigation controls for timeframe browsing, which will display the data for the timeframe before or after the current
      one.
      This is achieved via javascript:
        with an eventlistener for the buttons('click'), a new link is generated for the next and previous buttons(since the link is different every time). depending on the period, there is a new Date generated, which is either a day, week,.. before or after the current date. After calculating the date, a new url is generated: main route+period+newDate, and then the location of the window is adjusted to the new url.
      also there's the current date displayed, depending on the selected period. so the selected time is always transmitted with information on the date and time, but depending on the period, it's either displaying the corresponding day, week, month, or year.

    After the controls some statistics and then the chart itself is displayed.
    the statistics (average, min and max value, and data points) are calculated in python and are displayed as cards. the values are assembled from the value itself and the unit of the data.

    the chart is made with chart.js (script is included)
    its a 'line'-chart and displays wichever parameter is selected, it knows which is selected through the transmitted data while rendering the pdf. the label consists of the values of 'name' and 'unit'. and the sensordata is mapped by datatype.
    for the labels of the x-axis (time), they need to change for the different periods(for day: each hour, for week: the weekdays, for month: each day of the month, for year: each month)
    so to achieve that there is a block 'canvas', which is extended by 4 html files:
    -chart_day.html
    -chart_week.html
    -chart_month.html
    -chart_year.html
    wichever period is selected a different html is rendered with the respecctive labels

result_table.html
  extends layout.html. is generated with the route "/table" via "POST"
  displays server-side generated data tables

style.css
  contains custom modifications to the bootstrap styles. Primarily adjusts the btn-primary color to match the color of the chart


app.py
  is the heart of the Flask application, where all the server-side logic happens.
  First, I've imported all the necessary libraries:

  - Flask and its components for web functionality
  - CSV and pandas for data handling
  - datetime for time calculations
  - numpy for mathematical operations
  - other helper functions

  The app has several main routes:
  route("/"):
    This is the landing page route - it's super simple and just renders index.html without any data processing.
    (in the beginning I read all the data from the csv file and displayed it in the index.html on the initial page load, but as I explained the dataset has the potential to get really big, so I didn't want to get all the data everytime someone opens the website, which would be quite expensive. Rather the user gets the possibility to select the data she wants to see later on)

  route("/table"), methods=["POST"]:
    This route handles the table generation. Before processing any data, I define two important dictionaries:

    AVAILABLE_PARAMETERS: links the parameter names from the html (like 'humidity') to their CSV column names (like 'rht_humidity')
    TIMEFRAME_OPTIONS: defines the predefined time ranges like 'last_hour', 'last_day', etc.

    When the route is called, it:

      - Gets the selected parameters from the form and checks if all the necessary data is provided and checks for errors in the data
      - Reads the CSV file using pandas
      - Filters the data based on the selected timeframe
      - Formats the data nicely (rounding numbers, renaming columns)
      - Converts the dataframe to an HTML table
      - Renders it all in result_table.html


  route("/chart/"):
  This is actually three routes in one! It can handle:

  /chart/
  /chart/<period>
  /chart/<period>/<date>

  Besides the info which is directly transmitted via the route (period and day), there's also a form in chart.html, where you can select the datatype you're interested in. If nothing is specified, it defaults to period="day", the current date, and dataype="humidity.
  The route:

  - Validates the period (must be day, week, month, or year) and sets it to default if nothing else is selected
  - validated datatype and sets it to default ('rht_humidity') if nothing else is selected
  - Calculates the correct start and end dates based on the period(start date is always monday, first day of the month/year, and start at
    0:00am )
  - Gets the sensor data using fetch_data()
  - Processes the data with process_data()
  - Calculates statistics (average, min, max) with the functions from the numpy library
  - Renders the appropriate chart template with all the processed data



  There are also two helper functions:

  fetch_data():
  This function reads the CSV file and returns data for the specified timeframe and datatype. It's like a data fetcher that only gets what is needed.
  process_data():
  This is where the data is adjustet, so it can be displayed in the chart accordingly. It:

  Aggregates the data based on the period (hourly for days, daily for weeks/months, monthly for years)- this is necessary since there is new data every minute and we don't want so many datapoints in our chart. so depending on which period is selected, the data gets aggregated to a fixed amount of points
  Fills in gaps where there's no data
  Returns everything in a format that chart.js can understand

  All this processing ensures that whether you're looking at a day's worth of temperature readings or a year's worth of humidity data, you get a clean, well-formatted visualization that's easy to understand. The route and function structure makes it easy to modify or add new features later, which was important since this started as a simple project to help display sensor data more appealingly.



Key Features of the overall application:

    Time-range based data filtering
    Dynamic chart generation
    Customizable parameter selection
    Responsive design
    Interactive navigation controls
    Statistical summaries
    Multiple visualization options (tables and charts)

The application successfully transforms raw sensor data into an intuitive, user-friendly interface for monitoring environmental parameters. The modular design allows for easy maintenance and future enhancements.










