import io
import logging
import datetime as dt

from flask import render_template, request, redirect, url_for, flash

from dash_plot import init_dashboard

from common import app, gcs_client, bucket, publisher


def getDates():
    today = dt.date.today()
    return {"days": [
        str(today - dt.timedelta(days=i))
        for i in range(1, 8)],
            "hours": [
                f'{i:02}'
                for i in range(24)],
            "minutes": [
                f'{i:02}'
                for i in range(60)],
            "seconds": [
                f'{i:02}'
                for i in range(60)]}


@app.route('/', methods=['GET'])
def index():
    blobs = [blob
             for blob in gcs_client.list_blobs(bucket)
             if blob.name.startswith(f'{app.config["FOLDER_NAME"]}/output')]

    return render_template('index.html', blobs=blobs)


@app.route("/content", methods=['GET'])
def content():
    blob_name = request.args["name"]
    blob_content = io.BytesIO()

    gcs_client.download_blob_to_file(
        f"gs://{app.config['CLOUD_STORAGE_BUCKET']}/{blob_name}", blob_content)
    # df = pd.read_csv(io.StringIO(blob_content.getvalue().decode("utf-8")))

    return blob_content.getvalue().decode("utf-8").replace("\n", "<br/>")


@app.route('/fetch-data', methods=["GET", "POST"])
def fetchData():
    if request.method == 'GET':
        return render_template('fetch-data.html', **getDates())

    day_input = request.form.get('day')
    hr_input = request.form.get('hour')
    min1_input = request.form.get('minute1')
    min2_input = request.form.get('minute2')
    sec1_input = request.form.get('second1')
    sec2_input = request.form.get('second2')

    input = day_input + "-" + hr_input + "-" + min1_input + "_" + sec1_input + "-" + min2_input + "_" + sec2_input
    input = input.encode('utf-8')
    topic_path = publisher.topic_path(app.config['GOOGLE_CLOUD_PROJECT'],
                                      app.config['PUB_TOPIC'])
    future = publisher.publish(topic_path, input)
    future.result()

    flash("""
Requst to download data from pi has been sent.
Please wait for it to be loaded into the bucket""")
    return redirect(url_for('index'))


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


app = init_dashboard(app)

if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END app]
