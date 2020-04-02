axios = require('axios')

module.exports = function (fastify, opts, done) {

    fastify.post('/retrieve_season_stats', async(req, res) => {

        player_id = req.body.player_id
        platform = req.body.platform
        perspective = req.body.perspective

        player_obj = {
            player_id: player_id,
            perspective: perspective,
            platform: platform
        }

        let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_season_stats', player_obj)

        if(api_response.status == 200){
            data = api_response.data
            return res.send(data)
        } else {
            console.log(api_response)
        }
    })

    done()
}