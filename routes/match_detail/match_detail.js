axios = require('axios'),

module.exports = function (fastify, opts, done) {

    fastify.get('/match_detail/:match_id/', async(req, res) => {
        match_id = req.params.match_id

        let url = `http://127.0.0.1:8000/api/match_detail/${match_id}/`

        let api_response = await axios.get(url)

        if(api_response.status == 200){
  
            telemetry_data = api_response.data.telemetry_data

            return res.view('match_detail.html', {
                telemetry_data: telemetry_data
            }) 
        } else {
            console.log(api_response)
        }
    })

    done()

}