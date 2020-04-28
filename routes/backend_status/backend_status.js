utlity = require('../../utility'),
axios = require('axios')

module.exports = function (fastify, opts, done) {

    fastify.get('/backend_status', async(req, res) => {

        utlity.checkStatus(false, true, true)
        .then(function(result) {
            return res.send({
                backend_status: result
            })
        })
        .catch(error => {
            console.log(error)
        })
    })

    done()
}