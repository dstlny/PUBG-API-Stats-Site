axios = require('axios')

async function checkStatusPromise(){
	return await axios.get('http://127.0.0.1:8000/api/status')
	.then(api_response => {
		if(api_response.status == 200 && api_response.data.status == 'OK'){
			return true
		} else {
			return false
		}
	})
	.catch(error => {
		return false
	})
}

function checkStatusLog(){
	axios.get('http://127.0.0.1:8000/api/status')
	.then(api_response => {
		if(api_response.status == 200 && api_response.data.status == 'OK'){
			console.log(`Backend Django service up and running on port ${8000}!`)
		}
	})
	.catch(error => {
		console.log(`Seems Backend services are down...`)
	})
}

function checkStatusReturn(){
	axios.get('http://127.0.0.1:8000/api/status')
	.then(api_response => {
		if(api_response.status == 200 && api_response.data.status == 'OK'){
			return false
		}
	})
	.catch(error => {
		return true
	})
}

module.exports = {
	checkStatusPromise: checkStatusPromise,
	checkStatusLog: checkStatusLog,
	checkStatusReturn: checkStatusReturn
}