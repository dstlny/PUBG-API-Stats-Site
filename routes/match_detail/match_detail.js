const axios = require('axios')
const util = require('util')

module.exports = function (fastify, opts, done) {
	
	const django_ip = fastify.django_ip
	
	fastify.get('/match_detail/:match_id/', async (req, res) => {

		let url = `http://${django_ip}:8000/api/match_detail/${req.params.match_id}/`

		let api_response = await axios.get(url)
		
		if (api_response.status == 200) {
			
			let urls = []
			let platform = api_response.data.telemetry_data.platform
			let player_name = api_response.data.telemetry_data.player_data.player_name
			urls.push({href: `/user/${player_name}/platform/${platform}/`, text: `${player_name}'s profile`})

			return res.view('match_detail.html', {
				telemetry_data: api_response.data.telemetry_data,
				base_address: fastify.base_address,
				urls: urls
			})
		} else {
			console.log(api_response)
		}
	})

	done()

}