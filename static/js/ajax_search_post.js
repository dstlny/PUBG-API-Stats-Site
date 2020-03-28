var table;
var retrieved = false
var requested = true
var no_natches = true

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

		event.preventDefault();

		if(!(retrieved)){
			hideInitial();
		}

		callForm()

	});

});

function clearAll(windowObject) {
	var id = Math.max(
		windowObject.setInterval(noop, 1000),
		windowObject.setTimeout(noop, 1000)
	);
  
	while (id--) {
		windowObject.clearTimeout(id);
		windowObject.clearInterval(id);
	}
  
	function noop(){}
}

function loadResultsDataTable(){

	$("div.alert").remove();
	$('#datatable_container').show();

	table = $('#results_datatable').DataTable({
		"ajax": {
			"url": $("#retrieve_matches")[0].value,
			"type": 'POST',
			"data": {
				player_id: document.getElementById('player_id').value,
				platform: document.getElementById('id_platform').value,
				game_mode: document.getElementById('id_game_mode').value,
				perspective: document.getElementById('id_perspective').value,
			},
			"dataSrc": function(data){
				if(typeof data.message !== 'undefined' && data.message !== undefined || typeof data.data !== 'undefined' && data.data !== undefined){
					showMessages(data)
					requested = true
					no_matches = false
					return data.data
				} else if(typeof data.error !== 'undefined' && data.error !== undefined){
					showMessages(data)
					requested = false
					no_natches = true
					return []
				}
			}
		},
		"paging": true,
		"bFilter": true,
		"bLengthChange": true,
		"columns": [
			{ width: '8%', data: "map" },
			{ width: '8%', data: "mode" },
			{ width: '8%', data: 'custom_match' },
			{ width: '10%', data: "date_created", type: "date" },
			{ width: '10%', data: "team_placement" },
			{ width: '40%', data: "team_details" },
		],
		'pageLength': 25,
		"order": [[ 3, "asc" ]],
		"processing": true,
		"language": {
			processing: '<i class="fa fa-spinner fa-spin fa-fw"></i><span class="sr-only">Loading...</span> '
		},
	});

	if(requested && table !== undefined){
		setInterval(function() {
			table.ajax.reload(null, false);
		}, 5000);
	}

	if(!(retrieved)){
		setTimeout(function(){
			retrievePlayerSeasonStats()
		}, 15000);
   	}
	
	seasonStatToggle(document.getElementById('id_perspective').value)

}

function showMessages(data){
	$("div.alert").remove();
	var messages = document.getElementById("messages")
	if(data.message){
		var message_html = `<div class="alert alert-success" role="alert">
		<i class="fa fa-check"></i>&nbsp;&nbsp;${data.message}
		</div>`
		messages.innerHTML += message_html
	}
	if(data.error){
		var error_html = `<div class="alert alert-warning" role="alert">
			<i class="fa fa-exclamation-triangle"></i>&nbsp;&nbsp;${data.error}
		</div>`
		messages.innerHTML += error_html
	}
}

function destroyDataTable(){
	$('#results_datatable').DataTable().destroy();
}

function callForm(){
	var form_data = $('#search_form').serialize();
	var form_method = $('#search_form').attr('method')
	clearAll(window);

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
		type: form_method,
		url: $('#search_form').attr('action'),
		success: function (data, status, xhr) {
			$("div.alert").remove();
			destroyDataTable();
			
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
		},
		error: function(XMLHttpRequest, textStatus, errorThrown) { 
			alert("Status: " + textStatus); alert("Error: " + errorThrown); 
		}       
	});
}

function seasonStatToggle(perspective) {

	if(!(no_natches)){
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

function retrievePlayerSeasonStats(){
	var api_id = document.getElementById('player_id').value
	var platform = document.getElementById('id_platform').value
	var perspective = document.getElementById('id_perspective').value
	var season_endpoint = document.getElementById('season_stats_endpoint').value

	extra_elems = []

	if(!(no_natches)){

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
							var element = document.getElementById(entry)
							
							console.log(entry, element)

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
