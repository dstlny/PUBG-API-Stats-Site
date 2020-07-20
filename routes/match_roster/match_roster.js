const axios = require('axios')

module.exports = function (fastify, opts, done) {

	const django_ip = fastify.django_ip

	fastify.get('/match_rosters/:match_id/', async (req, res) => {

		let url = `http://${django_ip}:8000/api/match_rosters/${req.params.match_id}/`
		
		axios.get(url).then(function (api_response) {
			return res.send({
				rosters: api_response.data,
				base_address: fastify.base_address
			})
		}).catch(function (error) {
			return res.view('error.html')
		})
	
	})

	done()

}