let table;
let retrieved = false
let requested = true
let no_matches = true
let tries = 0;
let down = false

$(document).ready(function() {

	function hideInitial(){
		$('#seasons_container').hide();
		$("div.alert").remove();
		destroyDataTable();
		$('#results_datatable').DataTable({
			'pageLength': 25,
			"order": [[ 3, "asc" ]],
			'language':{
				emptyTable: 'Please enter a players name and press the <i class="fa fa-search"></i> icon'
			}
		});
	}

	hideInitial();

	$(document).on('submit', 'form#search_form', function(event){

		event.preventDefault()

		if(!retrieved){
			hideInitial();
		}

		callForm()

	});

});

function clearAll(windowObject) {
	let id = Math.max(
		windowObject.setInterval(noop, 1000),
		windowObject.setTimeout(noop, 1000)
	);
  
	while (id--) {
		windowObject.clearTimeout(id);
		windowObject.clearInterval(id);
	}
  
	function noop(){}
}

function seasonStatsHasShown(){
	return $('#tpp_row').is(':visible') || $('#fpp_row').is(':visible')
}

function loadResultsDataTable(){

	$("div.alert").remove();
	$('#datatable_container').show();

	table = $('#results_datatable').DataTable({
		ajax: {
			url: $("#retrieve_matches")[0].value,
			type: 'POST',
			data: {
				player_id: document.getElementById('player_id').value,
				platform: document.getElementById('id_platform').value,
				game_mode: document.getElementById('id_game_mode').value,
				perspective: document.getElementById('id_perspective').value,
			},
			async: true,
			dataSrc: function(data){
				if(typeof data.message !== 'undefined' && data.message !== undefined || typeof data.data !== 'undefined' && data.data !== undefined){
					showMessages(data)
					requested = true
					no_matches = false
					return data.data
				} else if(typeof data.error !== 'undefined' && data.error !== undefined){
					showMessages(data)
					requested = false
					no_matches = true
					return []
				}
			},
			error: function (xhr, error, code){
				tries += 1.

				if(tries > 6){
					showMessages({
						error: 'Connection has timed out. This has been logged.'
					})
				}
				checkDown()
            }
		},
		paging: true,
		bFilter: true,
		bLengthChange: true,
		columns: [
			{ width: '8%', data: "map" },
			{ width: '8%', data: "mode" },
			{ width: '8%', data: 'custom_match' },
			{ width: '10%', data: "date_created", type: "datetime" },
			{ width: '10%', data: "team_placement" },
			{ width: '40%', data: "team_details" },
			{ width: '10%', data: "actions" },
		],
		pageLength: 25,
		order: [[ 3, "desc" ]],
		processing: true,
		language: {
			processing: '<i class="fa fa-spinner fa-spin fa-fw"></i><span class="sr-only">Loading...</span> '
		},
	});

	if(requested && table !== undefined){
		ajax_interv = setInterval(function() {
			table.ajax.reload(null, false);
		}, 5000);
	}
	
	if(!seasonStatsHasShown() && requested && !down){
		retrievePlayerSeasonStats()
   	}

}

function showMessages(data){
	$("div.alert").remove();
	let messages = document.getElementById("messages")
	if(data.message){
		let message_html = `<div class="alert alert-success" role="alert">
		<i class="fa fa-check"></i>&nbsp;&nbsp;${data.message}
		</div>`
		messages.innerHTML += message_html
	}
	if(data.error){
		let error_html = `<div class="alert alert-warning" role="alert">
			<i class="fa fa-exclamation-triangle"></i>&nbsp;&nbsp;${data.error}
		</div>`
		messages.innerHTML += error_html
	}
}

function destroyDataTable(){
	$('#results_datatable').DataTable().destroy();
	$('#results_datatable tbody').empty();
}

function callForm(){
	clearAll(window);
	$("div.alert").remove();
	destroyDataTable();
	$('#seasons_container').hide();

	let form_data = $('#search_form').serialize();

	player_name = document.getElementById("id_player_name").value

	if(player_name !== undefined && typeof player_name !== 'undefined'){
		last_player_name = document.getElementById('player_name').value
		if(last_player_name !== undefined && typeof last_player_name !== 'undefined'){
			if(player_name.trim() == last_player_name.trim()){
				retrieved = true
			} else {
				retrieved = false
			}
		} else {
			retrieved = false
		}
	}
	
	$.fn.dataTable.ext.errMode = 'error';

	$.ajax({
		data: form_data,
		type: 'POST',
		url: $('#search_form').attr('action'),
		async: true,
		success: function (data, status, xhr) {
			
			if(data.error == undefined){
				if(data.player_id){
					document.getElementById('player_id').value = data.player_id
				}
				if(data.player_name){
					document.getElementById('player_name').value = data.player_name
				}
				loadResultsDataTable();	
			} else {
				showMessages(data)
				$('#seasons_container').hide();
				$('#datatable_container').hide();
			}
		}     
	});
}

function seasonStatToggle(perspective) {

	if(!no_matches){
		switch(perspective){
			case 'fpp':
				$('#fpp_row').show()
				$('#tpp_row').hide()
				break;
			case 'tpp':
				$('#tpp_row').show()
				$('#fpp_row').hide()
				break;
			default:
				$('#fpp_row').show()
				$('#tpp_row').show()
				break;
		}
	}

}

function checkDown(){
	$.ajax({
		type: 'GET',
		url:'/backend_status',
		async: true,
		success: function (data, status, xhr) {
			if(data.backend_status == true){
				down = true
			}
		}     
	});
}

function retrievePlayerSeasonStats(){
	let api_id = document.getElementById('player_id').value
	let platform = document.getElementById('id_platform').value
	let perspective = document.getElementById('id_perspective').value
	let season_endpoint = document.getElementById('season_stats_endpoint').value

	extra_elems = []

	if(!no_matches || !retrieved){

		$.ajax({
			data: {
				player_id: api_id,
				platform: platform,
				perspective: perspective,
			},
			type: 'POST',
			url: season_endpoint,
			success: function (data, status, xhr) {
				data.forEach(function(arrayItem) {
					Object.entries(arrayItem).forEach(([key, val]) => {
						for(let entry in val){
							let element = document.getElementById(entry)
							
							if(entry.includes('season_stats')){
								extra_elems.push(`${entry}_container`)
							}

							element.innerHTML = `${val[entry]}`
						}
					});
				});
				$('#seasons_container').show();
				retrieved = true

				for(let element in extra_elems){
					$(element).show()
				}

				seasonStatToggle(perspective)
			}
		});

	}

}
