const utlity = require('../../utility')
const axios = require('axios')

module.exports = function (fastify, opts, done) {
	
	fastify.get('/backend_status', async(req, res) => {

		utlity.checkStatusPromise()
		.then(function(result) {
			return res.send({
				backend_status: result
			})
		})

	})

	done()
}