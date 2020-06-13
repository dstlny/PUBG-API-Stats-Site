const axios = require('axios')

module.exports = function (fastify, opts, done) {

	const django_ip = fastify.django_ip

	fastify.get('/match_rosters/:match_id/', async (req, res) => {

		let url = `http://${django_ip}:8000/api/match_rosters/${req.params.match_id}/`
		
		let api_response = await axios.get(url)
		
		if (api_response.status == 200) {
			return res.send({
				rosters: api_response.data,
				base_address: fastify.base_address
			})
		} else {
			console.log(api_response)
		}
	})

	done()

}