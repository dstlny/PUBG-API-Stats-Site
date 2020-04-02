const fastify = require('fastify'),
	  app = fastify(),
	  path = require('path'),
	  utlity = require('./utility')

app.register(require('fastify-formbody'))

app.register(require('point-of-view'), {
	engine: {
		nunjucks: require('nunjucks')
	},
	templates: './templates/',
  	includeViewExtension: false
})

app.register(require('fastify-static'), {
	root: path.join(__dirname, 'static'),
	prefix: '/static/', // optional: default '/'
})

app.register(require('./routes/index/index'))
app.register(require('./routes/search/search'))
app.register(require('./routes/retrieve_season_stats/retrieve_season_stats'))
app.register(require('./routes/retrieve_matches/retrieve_matches'))
app.register(require('./routes/backend_status/backend_status'))

app.listen(7009, () => {
	console.log(`NodeJS up and running on port ${7009}!`)
	utlity.checkStatus(true, false, false)
})