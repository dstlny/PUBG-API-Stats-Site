const axios = require('axios')

module.exports = function (fastify, opts, done) {

	const django_ip = fastify.django_ip

	fastify.post('/retrieve_season_stats', async(req, res) => {

		let player_obj = {
			player_id: req.body.player_id,
			perspective: req.body.perspective,
			platform: req.body.platform
		}

		let api_response = await axios.post(`http://${django_ip}:8000/api/retrieve_season_stats`, player_obj)

		if(api_response.status == 200){
			return res.send(api_response.data)
		} else {
			console.log(api_response)
		}
	})

	done()
}