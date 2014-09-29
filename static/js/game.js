'use strict';

var Game = Backbone.Model.extend({
	urlRoot: '/games',

	initialize: function(attributes, options) {
		this.players = new Players([], {
			'game': this
		});
	},
});

var Player = Backbone.Model.extend({
});

var Players = Backbone.Collection.extend({
	model: Player,

	url: function() {
		return this.game.url() + '/players';
	},

	comparator: function(player) {
		return -player.get('score');
	},

	initialize: function(models, options) {
		this.game = options['game'];

		this.listenTo(this, 'reset change', this.sort);
	}
});

var ScoreBoard = Backbone.View.extend({
	template: _.template(
		'<table>' +
			'<thead>' +
				'<tr>' +
					'<th></th>' +
					'<th>Player</th>' +
					'<th>Moves</th>' +
					'<th>Score</th>' +
				'</tr>' +
			'</thead>' +

			'<tbody>' +
			'<% players.each(function(player, position) { %>' +
				'<tr>' +
					'<td><%- (position + 1) %></td>' +
					'<td><%- player.id %></td>' +
					'<td><%- player.get("moves") %></td>' +
					'<td><%- player.get("score") %></td>' +
				'</tr>' +
			'<% }) %>' +
			'</tbody>' +
		'</table>'
	),

	initialize: function() {
		this.listenTo(this.model.players, 'sort', this.render);
		this.listenTo(this.model.players, 'sync', function(collection, response, options) {
			//TODO if is_active
			console.log(collection);
			if (true) {
				collection.fetch();
			}
		});

		this.model.players.fetch();
	},

	render: function() {
		this.$el.html(this.template({
			'players': this.model.players
		}));
	}
})

var PlayerBoard = Backbone.View.extend({
	template: _.template(
		'<table>' +
		'<% for (var x = 0; x < board.length; ++x) { %>' +
			'<tr>' +
			'<% for (var y = 0; y < board[x].length; ++y) { %>' +
				'<td><%- ARROWS[board[x][y].direction] %></td>' +
			'<% } %>' +
			'</tr>' +
		'<% } %>' +
		'</table>'
	),

	initialize: function() {
		this.listenTo(this.model, 'change', this.render);
		this.listenTo(this.model, 'sync', function(model, response, options) {
			if (model.get('moves')) {
				model.fetch();
			}
		});

		this.model.fetch();
	},

	render: function() {
		var ARROWS = {
			'up': '^',
			'down': 'v',
			'left': '<',
			'right': '>',
		};
		var board = this.model.get('board');

		this.$el.empty();
		this.$el.append($('<h3>').html('player:' + this.model.id + ' <small>points:' + this.model.get('score') + ' moves:' + this.model.get('moves') + '</small>'));

		if (board) {
			this.$el.append(this.template({
				'board': board,
				'ARROWS': ARROWS,
			}));
		}
	},
});
