const fastify = require('fastify'),
	  app = fastify(),
	  path = require('path'),
	  constants = require('./constants'),
	  axios = require('axios')
	  
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

// Declare a route
app.get('/', async(req, res) => {
	return res.view('index.html', {
		platform_selections: constants.PLATFORM_SELECTIONS,
		gamemode_selections: constants.GAMEMODE_SELECTIONS,
		perspective_selections: constants.PERSPECTIVE_SELECTIONS
	}) 
})

app.post('/search', async(req, res) => {
	player_name = req.body.player_name
	platform = req.body.platform
	perspective = req.body.perspective
	game_mode = req.body.game_mode

	player_obj = {
		player_name: player_name,
		game_mode: game_mode,
		perspective: perspective,
		platform: platform
	}

	let api_response = await axios.post('http://127.0.0.1:8000/api/search', player_obj)

	if(api_response.status == 200){
		error = api_response.data.error
		player_id = api_response.data.player_id
		player_name = api_response.data.player_name

		if(error !== undefined){
			return res.send({
				error: error,
				player_id: null
			})
		} else {
			if(player_id !== undefined){
				return res.send({
					player_id: player_id,
					player_name: player_name
				})
			}
		}
	} else { 
		console.error(api_response)
	}
})

app.post('/retrieve_matches', async(req, res) => {
	player_id = req.body.player_id
	platform = req.body.platform
	perspective = req.body.perspective
	game_mode = req.body.game_mode

	player_obj = {
		player_id: player_id,
		game_mode: game_mode,
		perspective: perspective,
		platform: platform
	}

	let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_matches', player_obj)

	if(api_response.status == 200){
		message = api_response.data.message
		data = api_response.data.data
		player_id = api_response.data.api_id
		error = api_response.data.error

		return res.send({
			message: message,
			data: data,
			player_id: player_id,
			error: error
		})
	} else {
		console.log(api_response)
	}
})

app.post('/retrieve_season_stats', async(req, res) => {
	player_id = req.body.player_id
	platform = req.body.platform
	perspective = req.body.perspective

	player_obj = {
		player_id: player_id,
		perspective: perspective,
		platform: platform
	}

	let api_response = await axios.post('http://127.0.0.1:8000/api/retrieve_season_stats', player_obj)

	if(api_response.status == 200){
		data = api_response.data
		return res.send(data)
	} else {
		console.log(api_response)
	}
})

app.listen(7009, () => {

	console.log(`NodeJS up and running on port ${7009}!`)

	axios.get('http://127.0.0.1:8000/api/status')
	.then(api_response => {
		if(api_response.status == 200 && api_response.data.status == 'OK'){
			console.log(`Backend Django service up and running on port ${8000}!`)
		}
	})
	.catch(error => {
		if(error.code == 'ECONNREFUSED'){
			console.log(`Seems Backend services are down...`)
		}
	})
})
