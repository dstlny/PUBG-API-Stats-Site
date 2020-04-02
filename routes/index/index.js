constants = require('../../constants'),
axios = require('axios'),

module.exports = function (fastify, opts, done) {

    fastify.get('/', async(req, res) => {
        return res.view('index.html', {
            platform_selections: constants.PLATFORM_SELECTIONS,
            gamemode_selections: constants.GAMEMODE_SELECTIONS,
            perspective_selections: constants.PERSPECTIVE_SELECTIONS
        }) 
    })

    done()
  }