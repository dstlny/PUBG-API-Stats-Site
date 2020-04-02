axios = require('axios')

module.exports = function (fastify, opts, done) {
    
    fastify.post('/search', async(req, res) => {
        player_name = req.body.player_name
        platform = req.body.platform
        perspective = req.body.perspective
        game_mode = req.body.game_mode

        player_obj = {
            player_name: player_name,
            game_mode: game_mode,
            perspective: perspective,
            platform: platform
        }

        let api_response = await axios.post('http://127.0.0.1:8000/api/search', player_obj)

        if(api_response.status == 200){
            error = api_response.data.error
            player_id = api_response.data.player_id
            player_name = api_response.data.player_name

            if(error !== undefined){
                return res.send({
                    error: error,
                    player_id: null
                })
            } else {
                if(player_id !== undefined){
                    return res.send({
                        player_id: player_id,
                        player_name: player_name
                    })
                }
            }
        } else { 
            console.error(api_response)
        }
    })

    done()
}