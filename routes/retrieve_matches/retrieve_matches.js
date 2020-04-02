axios = require('axios'),

module.exports = function (fastify, opts, done) {

    fastify.post('/retrieve_matches', async(req, res) => {
        player_id = req.body.player_id
        platform = req.body.platform
        perspective = req.body.perspective
        game_mode = req.body.game_mode

        player_obj = {
            player_id: player_id,
            game_mode: game_mode,
            perspective: perspective,
            platform: platform
        }

        let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_matches', player_obj)

        if(api_response.status == 200){
            message = api_response.data.message
            data = api_response.data.data
            player_id = api_response.data.api_id
            error = api_response.data.error

            return res.send({
                message: message,
                data: data,
                player_id: player_id,
                error: error
            })
        } else {
            console.log(api_response)
        }
    })

    done()

}