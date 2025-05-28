## Usage
Example:

```bash
export HOST='dwxibclsql03.northamerica.cerner.net'
export USER='service'
export PASSWORD='XXX'
export DATABASE='laborders_c1801_qasystem'

Example output:

<pre> ```bash sy018616-mac:Note sy018616$ python3 generate_db_data.py INFO:__main__:Connection to the database successful INFO:__main__:Number of rows in assay_status before insertion: 12044360 INFO:__main__:Changes committed successfully INFO:__main__:Number of rows in assay_status after insertion: 13043099 INFO:__main__:Connection closed successfully ``` </pre>
