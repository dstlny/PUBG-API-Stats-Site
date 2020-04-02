axios = require('axios')

function checkStatus(log, answer, promise){
	if(promise == true)
		return new Promise((resolve, reject) => {
			axios.get('http://127.0.0.1:8000/api/status')
			.then(api_response => {
				if(api_response.status == 200 && api_response.data.status == 'OK'){
					if(log === true)
						console.log(`Backend Django service up and running on port ${8000}!`)
					if(answer === true)
						resolve(false);
				}
			})
			.catch(error => {
				if(log === true)
					console.log(`Seems Backend services are down...`)
				if(answer === true)
					resolve(true);
			})
		});
	else
		axios.get('http://127.0.0.1:8000/api/status')
		.then(api_response => {
			if(api_response.status == 200 && api_response.data.status == 'OK'){
				if(log === true)
					console.log(`Backend Django service up and running on port ${8000}!`)
				if(answer === true)
					return false
			}
		})
		.catch(error => {
			if(log === true)
				console.log(`Seems Backend services are down...`)
			if(answer === true)
				return true
		})
		
}

exports.checkStatus = checkStatus