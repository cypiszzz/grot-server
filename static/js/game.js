'use strict';

// for debug purposes
var pr = console.log.bind(console);

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
	},

	parse: function(response, options) {
		return response.players;
	}
});

var ScoreBoard = Backbone.View.extend({
	template: _.template(
		'<li id="player_<%- player.id %>">' +
			'<div class="avatar"><img src="http://robohash.org/<%- player.id %>"></img></div>' +
			'<div class="name"><%- player.id %></div>' +
			'<div class="moves"><%- player.moves %></div>' +
			'<div class="score"><%- player.score %></div>' +
		'</li>'
	),

	initialize: function() {

		var _this = this;
		var topHeight = 65;
		var boardHeight;
		var $main = $('.main');

		this.listenTo(this.model.players, 'sort', this.render);
		this.listenTo(this.model.players, 'sync', function(collection, response, options) {
			if (response.game.ended === false) {
				collection.fetch();
			}
		});

		this.model.players.fetch();

		this.playerEntryHeight = 50;
		this.columnWidth = 400;
		this.playersInColumn;
		$(window).on('resize', function() {
			boardHeight = $('body').height() - topHeight - 10;
			_this.playersInColumn = Math.floor((boardHeight - _this.playerEntryHeight - 20) / _this.playerEntryHeight);
			$main.css('height', boardHeight);
			_this.render();
		}).resize();
	},

	render: function() {
		for(var i = 0, player; i < this.model.players.models.length; i++) {

			player = this.model.players.models[i].attributes;
			var $playerEntry = this.$el.find('#player_'+player.id);
			if(!$playerEntry.get(0)) {
				$playerEntry = $(this.template({
					player: player
				}));
				this.$el.append($playerEntry);
			}

			$playerEntry.find('.moves').html(player.moves);
			$playerEntry.find('.score').html(player.score);

			var animate = {
				top: i * this.playerEntryHeight + this.playerEntryHeight + 20,
				left: 0
			};

			if(i + 1 > this.playersInColumn) {
				animate.left = 600;
				animate.top -= (this.playersInColumn + 1) * this.playerEntryHeight;
			}
			$playerEntry.stop(true).animate(animate, 300);
		}

		if(this.model.players.models.length < this.playersInColumn + 1) {
			this.$el.css({
				left: '50%',
				'margin-left': this.columnWidth * -1 / 2
			});
		} else {
			this.$el.css({
				left: 0,
				'margin-left': 0
			});
		}
	}
});

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
