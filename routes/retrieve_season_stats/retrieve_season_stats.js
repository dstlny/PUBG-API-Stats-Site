axios = require('axios')

module.exports = function (fastify, opts, done) {

	fastify.post('/retrieve_season_stats', async(req, res) => {

		let player_obj = {
			player_id: req.body.player_id,
			perspective: req.body.perspective,
			platform: req.body.platform
		}

		let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_season_stats', player_obj)

		if(api_response.status == 200){
			return res.send(api_response.data)
		} else {
			console.log(api_response)
		}
	})

	done()
}