const axios = require('axios')

module.exports = function (fastify, opts, done) {

	fastify.get('/match_rosters/:match_id/', async (req, res) => {

		let url = `http://127.0.0.1:8000/api/match_rosters/${req.params.match_id}/`
		
		let api_response = await axios.get(url)
		
		if (api_response.status == 200) {
			return res.send({
				rosters: api_response.data
			})
		} else {
			console.log(api_response)
		}
	})

	done()

}