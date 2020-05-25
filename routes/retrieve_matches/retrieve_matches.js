const axios = require('axios')

module.exports = function (fastify, opts, done) {

	fastify.post('/retrieve_matches', async(req, res) => {
		
		let player_obj = {
			player_id: req.body.player_id,
			game_mode: req.body.game_mode,
			perspective:  req.body.perspective,
			platform: req.body.platform,
			times_requested: req.body.times_requested,
			seen_match_ids: req.body.seen_match_ids
		}

		let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_matches', player_obj)

		if(api_response.status == 200){
			return res.send({
				message: api_response.data.message,
				data: api_response.data.data,
				player_id: api_response.data.api_id,
				error: api_response.data.error
			})
		} else {
			console.log(api_response)
		}
	})

	done()

}