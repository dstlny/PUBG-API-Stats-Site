'use strict';

var retrieved = false
var requested = true
var no_matches = true
var tries = 0;
var down = false
var times_requested = 0
var seen_match_ids = []
var season_requested = false
var table_rosters = {}
var roster_table;
var table; 


$(document).ready(function() {

	table = $('#results_datatable').DataTable({
		data: [],
		paging: true,
		bFilter: true,
		bLengthChange: true,
		columns: [
			{ 
				className:'details-control',
				orderable: false,
				data: null,
				defaultContent: '',
			},
			{ width: '10%' }, // map
			{ width: '10%' }, // mode
			{ width: '10%' }, // custom 
			{ width: '10%', type: "datetime" }, // created
			{ width: '10%' }, // placement
			{ width: '40%' }, // details
			{ width: '20%' }, // actions
		],
		pageLength: 25,
		order: [[ 3, "desc" ]],
		processing: true,
		language: {
			processing: '<i class="fa fa-spinner fa-spin fa-fw"></i><span class="sr-only">Loading...</span> ',
			emptyTable: 'Please enter a players name and press the <i class="fa fa-search"></i> icon'
		},
	});

	function hideInitial(){
		$('#seasons_container').hide();
		$("#disconnected").hide();
		$("#currently_processing").hide();
	}

	// Add event listener for opening and closing details
	$(`#results_datatable tbody`).on('click', 'td.details-control', function () {
		let tr = $(this).closest('tr');
		let id = tr[0].id
		let row = table.row(tr);

		let returned_obj = format_child_row(id)
		let datatable_id = returned_obj.datatable_id
		let html = returned_obj.html

		if (row.child.isShown()) {
			row.child.hide();
			tr.removeClass('shown');
		} else {
			row.child(html).show();
			get_roster_for_match(id, datatable_id)
			tr.addClass('shown');
		}
	});

	hideInitial();

	$(document).on('submit', 'form#search_form', function(event){

		$("#season_stats_button").click(function() {
			retrievePlayerSeasonStats()
		});

		event.preventDefault()

		if(!retrieved){
			hideInitial();
		}

		clearAll(window);
		$('#seasons_container').hide();
		callForm()

	});

});

function get_roster_for_match(match_id, datatable_id){

	let roster_table = $(`#${datatable_id}`).DataTable({
		columns: [
			{ width: '15%' }, // rank
			{ width: '85%' }, // rosters
		],
		order: [[ 0, "asc" ]],
		scrollY: "200px",
        scrollCollapse: true,
        paging: false
	});

	if(!table_rosters[datatable_id]){
		table_rosters[datatable_id] = {
			rosters: []
		}
	
		$.ajax({
			type: 'GET',
			url: `/match_rosters/${match_id}/`,
			async: true,
			success: function (data, status, xhr) {
				let rosters = data.rosters
				let i;
				let len;
				for (i = 0, len=rosters.length; i < len; i++){
					table_rosters[datatable_id].rosters.push(rosters[i])
					roster_table.row.add([
						rosters[i].roster_rank,
						rosters[i].participant_objects,
					]).draw(false)
				}
			}
		});
	} else {
		let rosters_for_datatable = table_rosters[datatable_id].rosters
		let i;
		let len;
		for (i = 0, len=rosters_for_datatable.length; i < len; i++){
			roster_table.row.add([
				rosters_for_datatable[i].roster_rank,
				rosters_for_datatable[i].participant_objects,
			]).draw(false)
		}
	}
}

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

function format_child_row(id) {
	// `d` is the original data object for the row
	let generated_datatable_id = `rosters_datatable_${id}`

	let generated_row_data =`
		<div class="col-md-12" style='padding: 10px;' id='${generated_datatable_id}_wrapper'>
			<div class="tab-pane fade show active" id="leaderboard" role="tabpanel" aria-labelledby="nav-home-tab">
				<table class='table table-condensed hover' id='${generated_datatable_id}' style='width: 100%'>
					<thead>
						<tr>
							<th width='20%%'>Rank</th>
							<th width='80%'>Team Details</th>
						</tr>
					</thead>
					<tbody>
					</tbody>
				</table>
			</div>
		</div>`

	let obj = {
		datatable_id: generated_datatable_id,
		html: generated_row_data
	}

  	return obj
}

function getResults(){

	var data = {
		player_id: document.getElementById('player_id').value,
		platform: document.getElementById('id_platform').value,
		game_mode: document.getElementById('id_game_mode').value,
		perspective: document.getElementById('id_perspective').value,
		times_requested: times_requested,
		seen_match_ids: seen_match_ids
	}

	$.ajax({
		url: $("#retrieve_matches")[0].value,
		async: true,
		type:'POST',
		data: data,
		success: function(result){
			if(result.data){
				let i;
				let match_id;
				let len;
				document.getElementById('player_id').value = result.player_id
				for (i = 0, len=result.data.length; i < len; i++){
					match_id = result.data[i].id
					if(!seen_match_ids.includes(match_id)){
						seen_match_ids.push(match_id)
						let row_node = table.row.add([
							'',
							result.data[i].map,
							result.data[i].mode,
							result.data[i].custom_match,
							result.data[i].date_created,
							result.data[i].team_placement,
							result.data[i].team_details,
							result.data[i].actions
						]).node();
						$(row_node).attr("id", match_id);
					}
				}
				table.draw(false)
				times_requested += 1
				no_matches = false
				$('#seasons_container').show();
				$("#currently_processing").hide()
			}
		},
		error: function(xhr, error, code){
			tries += 1
			no_matches = true
			if(tries > 6){
				$("#disconnected").show()
			}
			checkDown()
		}
	});
	
}

function loadResultsDataTable(){

	getResults()

	setInterval(function() {
		getResults()
	}, 20000);

	seasonStatToggle(document.getElementById('id_perspective').value)

}


function callForm(){
	let form_data = $('#search_form').serialize();

	let player_name = document.getElementById("id_player_name").value

	if(player_name !== undefined && typeof player_name !== 'undefined'){
		let last_player_name = document.getElementById('player_name').value
		if(last_player_name !== undefined && typeof last_player_name !== 'undefined'){
			if(player_name.trim() == last_player_name.trim()){
				retrieved = true
				if(season_requested)
					season_requested = true
				else
					season_requested = false
			} else {
				retrieved = false
				season_requested = false
				$('#results_datatable').DataTable().clear().draw();
				seen_match_ids = []
				table_rosters = {}
				clearSeasonStats()
			}
		} else {
			retrieved = false
			season_requested = false
			$('#results_datatable').DataTable().clear().draw();
			seen_match_ids = []
			table_rosters = {}
			clearSeasonStats()
		}
	}

	times_requested = 0

	$.ajax({
		data: form_data,
		type: 'POST',
		url: $('#search_form').attr('action'),
		async: true,
		success: function (data, status, xhr) {
			if(data.player_id){
				document.getElementById('player_id').value = data.player_id
			}
			if(data.player_name){
				document.getElementById('player_name').value = data.player_name
			}
			if(!data.currently_processing || !data.error){
				loadResultsDataTable();	
			} else {
				if(data.error){
					$("#currently_processing").hide()
					$("#error").show()
					$("#error_message").text(data.error);
				} else {
					$("#error").hide()
					$("#currently_processing").show()
					setTimeout("loadResultsDataTable()", 20000);
				}
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

function clearSeasonStats(){
	document.getElementById('duo_season_matches').innerHTML = ''
	document.getElementById('duo_season_damage__figure').innerHTML = ''
	document.getElementById('duo_season_damage__text').innerHTML = ''
	document.getElementById('duo_season_headshots__figure').innerHTML = ''
	document.getElementById('duo_season_headshots__text').innerHTML = ''
	document.getElementById('duo_season_kills__figure').innerHTML = ''
	document.getElementById('duo_season_kills__text').innerHTML = ''
	document.getElementById('duo_season_longest_kill__figure').innerHTML = ''
	document.getElementById('duo_season_longest_kill__text').innerHTML = ''
	document.getElementById('duo_fpp_season_stats').innerHTML = ''
	document.getElementById('duo_fpp_season_matches').innerHTML = ''
	document.getElementById('duo_fpp_season_damage__figure').innerHTML = ''
	document.getElementById('duo_fpp_season_damage__text').innerHTML = ''
	document.getElementById('duo_fpp_season_headshots__figure').innerHTML = ''
	document.getElementById('duo_fpp_season_headshots__text').innerHTML = ''
	document.getElementById('duo_fpp_season_kills__figure').innerHTML = ''
	document.getElementById('duo_fpp_season_kills__text').innerHTML = ''
	document.getElementById('duo_fpp_season_longest_kill__figure').innerHTML = ''
	document.getElementById('duo_fpp_season_longest_kill__text').innerHTML = ''
	document.getElementById('solo_fpp_season_stats').innerHTML = ''
	document.getElementById('solo_fpp_season_matches').innerHTML = ''
	document.getElementById('solo_fpp_season_damage__figure').innerHTML = ''
	document.getElementById('solo_fpp_season_damage__text').innerHTML = ''
	document.getElementById('solo_fpp_season_headshots__figure').innerHTML = ''
	document.getElementById('solo_fpp_season_headshots__text').innerHTML = ''
	document.getElementById('solo_fpp_season_kills__figure').innerHTML = ''
	document.getElementById('solo_fpp_season_kills__text').innerHTML = ''
	document.getElementById('solo_fpp_season_longest_kill__figure').innerHTML = ''
	document.getElementById('solo_fpp_season_longest_kill__text').innerHTML = ''
	document.getElementById('solo_season_stats').innerHTML = ''
	document.getElementById('solo_season_matches').innerHTML = ''
	document.getElementById('solo_season_damage__figure').innerHTML = ''
	document.getElementById('solo_season_damage__text').innerHTML = ''
	document.getElementById('solo_season_headshots__figure').innerHTML = ''
	document.getElementById('solo_season_headshots__text').innerHTML = ''
	document.getElementById('solo_season_kills__figure').innerHTML = ''
	document.getElementById('solo_season_kills__text').innerHTML = ''
	document.getElementById('solo_season_longest_kill__figure').innerHTML = ''
	document.getElementById('solo_season_longest_kill__text').innerHTML = ''
	document.getElementById('squad_season_stats').innerHTML = ''
	document.getElementById('squad_season_matches').innerHTML = ''
	document.getElementById('squad_season_damage__figure').innerHTML = ''
	document.getElementById('squad_season_damage__text').innerHTML = ''
	document.getElementById('squad_season_headshots__figure').innerHTML = ''
	document.getElementById('squad_season_headshots__text').innerHTML = ''
	document.getElementById('squad_season_kills__figure').innerHTML = ''
	document.getElementById('squad_season_kills__text').innerHTML = ''
	document.getElementById('squad_season_longest_kill__figure').innerHTML = ''
	document.getElementById('squad_season_longest_kill__text').innerHTML = ''
	document.getElementById('squad_fpp_season_stats').innerHTML = ''.toUpperCase()
	document.getElementById('squad_fpp_season_matches').innerHTML = ''
	document.getElementById('squad_fpp_season_damage__figure').innerHTML = ''
	document.getElementById('squad_fpp_season_damage__text').innerHTML = ''
	document.getElementById('squad_fpp_season_headshots__figure').innerHTML = ''
	document.getElementById('squad_fpp_season_headshots__text').innerHTML = ''
	document.getElementById('squad_fpp_season_kills__figure').innerHTML = ''
	document.getElementById('squad_fpp_season_kills__text').innerHTML = ''
	document.getElementById('squad_fpp_season_longest_kill__figure').innerHTML = ''
	document.getElementById('squad_fpp_season_longest_kill__text').innerHTML = ''
}

function retrievePlayerSeasonStats(){
	let api_id = document.getElementById('player_id').value
	let platform = document.getElementById('id_platform').value
	let perspective = document.getElementById('id_perspective').value
	let season_endpoint = document.getElementById('season_stats_endpoint').value

	if(!season_requested){

		$("#season_stats").LoadingOverlay("show");

		$.ajax({
			data: {
				player_id: api_id,
				platform: platform,
				perspective: perspective,
			},
			type: 'POST',
			url: season_endpoint,
			async: true,
			success: function (data, status, xhr) {
				season_requested = true
				let len;
				for (let i = 0, len=data.length; i < len; i++){
					let row = data[i]

					if(row.duo_season_stats){
						let duo_season_stats = row.duo_season_stats
						document.getElementById('duo_season_stats').innerHTML = duo_season_stats.duo_season_stats.toUpperCase()
						document.getElementById('duo_season_matches').innerHTML = duo_season_stats.duo_season_matches
						document.getElementById('duo_season_damage__figure').innerHTML = duo_season_stats.duo_season_damage__figure
						document.getElementById('duo_season_damage__text').innerHTML = duo_season_stats.duo_season_damage__text
						document.getElementById('duo_season_headshots__figure').innerHTML = duo_season_stats.duo_season_headshots__figure
						document.getElementById('duo_season_headshots__text').innerHTML = duo_season_stats.duo_season_headshots__text
						document.getElementById('duo_season_kills__figure').innerHTML = duo_season_stats.duo_season_kills__figure
						document.getElementById('duo_season_kills__text').innerHTML = duo_season_stats.duo_season_kills__text
						document.getElementById('duo_season_longest_kill__figure').innerHTML = duo_season_stats.duo_season_longest_kill__figure
						document.getElementById('duo_season_longest_kill__text').innerHTML = duo_season_stats.duo_season_longest_kill__text
					}
					if(row.duo_fpp_season_stats){
						let duo_fpp_season_stats = row.duo_fpp_season_stats
						document.getElementById('duo_fpp_season_stats').innerHTML = duo_fpp_season_stats.duo_fpp_season_stats.toUpperCase()
						document.getElementById('duo_fpp_season_matches').innerHTML = duo_fpp_season_stats.duo_fpp_season_matches
						document.getElementById('duo_fpp_season_damage__figure').innerHTML = duo_fpp_season_stats.duo_fpp_season_damage__figure
						document.getElementById('duo_fpp_season_damage__text').innerHTML = duo_fpp_season_stats.duo_fpp_season_damage__text
						document.getElementById('duo_fpp_season_headshots__figure').innerHTML = duo_fpp_season_stats.duo_fpp_season_headshots__figure
						document.getElementById('duo_fpp_season_headshots__text').innerHTML = duo_fpp_season_stats.duo_fpp_season_headshots__text
						document.getElementById('duo_fpp_season_kills__figure').innerHTML = duo_fpp_season_stats.duo_fpp_season_kills__figure
						document.getElementById('duo_fpp_season_kills__text').innerHTML = duo_fpp_season_stats.duo_fpp_season_kills__text
						document.getElementById('duo_fpp_season_longest_kill__figure').innerHTML = duo_fpp_season_stats.duo_fpp_season_longest_kill__figure
						document.getElementById('duo_fpp_season_longest_kill__text').innerHTML = duo_fpp_season_stats.duo_fpp_season_longest_kill__text
					}
					if(row.solo_fpp_season_stats){
						let solo_fpp_season_stats = row.solo_fpp_season_stats
						document.getElementById('solo_fpp_season_stats').innerHTML = solo_fpp_season_stats.solo_fpp_season_stats.toUpperCase()
						document.getElementById('solo_fpp_season_matches').innerHTML = solo_fpp_season_stats.solo_fpp_season_matches
						document.getElementById('solo_fpp_season_damage__figure').innerHTML = solo_fpp_season_stats.solo_fpp_season_damage__figure
						document.getElementById('solo_fpp_season_damage__text').innerHTML = solo_fpp_season_stats.solo_fpp_season_damage__text
						document.getElementById('solo_fpp_season_headshots__figure').innerHTML = solo_fpp_season_stats.solo_fpp_season_headshots__figure
						document.getElementById('solo_fpp_season_headshots__text').innerHTML = solo_fpp_season_stats.solo_fpp_season_headshots__text
						document.getElementById('solo_fpp_season_kills__figure').innerHTML = solo_fpp_season_stats.solo_fpp_season_kills__figure
						document.getElementById('solo_fpp_season_kills__text').innerHTML = solo_fpp_season_stats.solo_fpp_season_kills__text
						document.getElementById('solo_fpp_season_longest_kill__figure').innerHTML = solo_fpp_season_stats.solo_fpp_season_longest_kill__figure
						document.getElementById('solo_fpp_season_longest_kill__text').innerHTML = solo_fpp_season_stats.solo_fpp_season_longest_kill__text
					}
					if(row.solo_season_stats){
						let solo_season_stats = row.solo_season_stats
						document.getElementById('solo_season_stats').innerHTML = solo_season_stats.solo_season_stats.toUpperCase()
						document.getElementById('solo_season_matches').innerHTML = solo_season_stats.solo_season_matches
						document.getElementById('solo_season_damage__figure').innerHTML = solo_season_stats.solo_season_damage__figure
						document.getElementById('solo_season_damage__text').innerHTML = solo_season_stats.solo_season_damage__text
						document.getElementById('solo_season_headshots__figure').innerHTML = solo_season_stats.solo_season_headshots__figure
						document.getElementById('solo_season_headshots__text').innerHTML = solo_season_stats.solo_season_headshots__text
						document.getElementById('solo_season_kills__figure').innerHTML = solo_season_stats.solo_season_kills__figure
						document.getElementById('solo_season_kills__text').innerHTML = solo_season_stats.solo_season_kills__text
						document.getElementById('solo_season_longest_kill__figure').innerHTML = solo_season_stats.solo_season_longest_kill__figure
						document.getElementById('solo_season_longest_kill__text').innerHTML = solo_season_stats.solo_season_longest_kill__text
					}
					if(row.squad_season_stats){
						let squad_season_stats = row.squad_season_stats
						document.getElementById('squad_season_stats').innerHTML = squad_season_stats.squad_season_stats.toUpperCase()
						document.getElementById('squad_season_matches').innerHTML = squad_season_stats.squad_season_matches
						document.getElementById('squad_season_damage__figure').innerHTML = squad_season_stats.squad_season_damage__figure
						document.getElementById('squad_season_damage__text').innerHTML = squad_season_stats.squad_season_damage__text
						document.getElementById('squad_season_headshots__figure').innerHTML = squad_season_stats.squad_season_headshots__figure
						document.getElementById('squad_season_headshots__text').innerHTML = squad_season_stats.squad_season_headshots__text
						document.getElementById('squad_season_kills__figure').innerHTML = squad_season_stats.squad_season_kills__figure
						document.getElementById('squad_season_kills__text').innerHTML = squad_season_stats.squad_season_kills__text
						document.getElementById('squad_season_longest_kill__figure').innerHTML = squad_season_stats.squad_season_longest_kill__figure
						document.getElementById('squad_season_longest_kill__text').innerHTML = squad_season_stats.squad_season_longest_kill__text
					}
					if(row.squad_fpp_season_stats){
						let squad_fpp_season_stats = row.squad_fpp_season_stats
						document.getElementById('squad_fpp_season_stats').innerHTML = squad_fpp_season_stats.squad_fpp_season_stats.toUpperCase()
						document.getElementById('squad_fpp_season_matches').innerHTML = squad_fpp_season_stats.squad_fpp_season_matches
						document.getElementById('squad_fpp_season_damage__figure').innerHTML = squad_fpp_season_stats.squad_fpp_season_damage__figure
						document.getElementById('squad_fpp_season_damage__text').innerHTML = squad_fpp_season_stats.squad_fpp_season_damage__text
						document.getElementById('squad_fpp_season_headshots__figure').innerHTML = squad_fpp_season_stats.squad_fpp_season_headshots__figure
						document.getElementById('squad_fpp_season_headshots__text').innerHTML = squad_fpp_season_stats.squad_fpp_season_headshots__text
						document.getElementById('squad_fpp_season_kills__figure').innerHTML = squad_fpp_season_stats.squad_fpp_season_kills__figure
						document.getElementById('squad_fpp_season_kills__text').innerHTML = squad_fpp_season_stats.squad_fpp_season_kills__text
						document.getElementById('squad_fpp_season_longest_kill__figure').innerHTML = squad_fpp_season_stats.squad_fpp_season_longest_kill__figure
						document.getElementById('squad_fpp_season_longest_kill__text').innerHTML = squad_fpp_season_stats.squad_fpp_season_longest_kill__text
					}

				}

				$("#season_stats").LoadingOverlay("hide", true);
				$('#seasons_container').show();
				
			}
		});

	}
}
