const fastify = require('fastify')({
	logger: true
})
const path = require('path')
const utlity = require('./utility')

fastify.register(require('fastify-formbody'))

fastify.register(require('point-of-view'), {
	engine: {
		nunjucks: require('nunjucks')
	},
	templates: './templates/',
	includeViewExtension: false
})

fastify.register(require('fastify-static'), {
	root: path.join(__dirname, 'static'),
	prefix: '/static/'
})

// routes
fastify.register(require('./routes/index/index'))
fastify.register(require('./routes/search/search'))
fastify.register(require('./routes/retrieve_season_stats/retrieve_season_stats'))
fastify.register(require('./routes/retrieve_matches/retrieve_matches'))
fastify.register(require('./routes/backend_status/backend_status'))
fastify.register(require('./routes/match_detail/match_detail'))
fastify.register(require('./routes/match_roster/match_roster'))

fastify.listen(7009, async function (err, address){
	if (err) {
		process.exit(1)
	}
	console.log(`NodeJS up and running on port ${address}!`)
	utlity.checkStatusLog()
})
