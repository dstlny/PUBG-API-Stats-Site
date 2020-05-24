axios = require('axios')

module.exports = function (fastify, opts, done) {
	
	fastify.post('/search', async(req, res) => {

		let player_obj = {
			player_name:  req.body.player_name,
			game_mode: req.body.game_mode,
			perspective: req.body.perspective,
			platform: req.body.platform
		}

		let api_response = await axios.post('http://127.0.0.1:8000/api/search', player_obj)

		if(api_response.status == 200){

			let error = api_response.data.error
			let player_id = api_response.data.player_id
			let currently_processing = api_response.data.currently_processing
			let no_new_matches = api_response.data.no_new_matches
			let message = api_response.data.message
			
			return res.send({
				player_id: player_id,
				player_name: api_response.data.player_name,
				currently_processing: currently_processing,
				no_new_matches: no_new_matches,
				message: message,
				error: error
			})
		} else { 
			console.error(api_response)
		}
	})

	done()
}